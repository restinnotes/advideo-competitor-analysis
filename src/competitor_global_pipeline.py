"""Competitor Global Pipeline - 竞品广告全局分析 Agent + 关键帧抽取"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from .bailian_client import BailianClient
from .config import Config
from .filename_utils import safe_filename
from .json_utils import parse_json_with_retry, save_json
from .logging_utils import setup_logger

logger = setup_logger(__name__)


# ─── safe_slug ───────────────────────────────────────────────────────────────

def _safe_slug(text: str, max_len: int = 40) -> str:
    """从 module_name 生成安全文件名片段。"""
    s = text.lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s or "module"


# ─── ffprobe ─────────────────────────────────────────────────────────────────

def _ffprobe_duration(video_path: str) -> float | None:
    """用 ffprobe 获取本地视频真实时长（秒）。"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe 失败: {e}")
    return None


# ─── JSON repair ─────────────────────────────────────────────────────────────

def _extract_json_object(text: str) -> str:
    """从模型输出中提取第一个顶层 JSON 对象。"""
    text = text.strip()
    # strip markdown code block
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # find first {
    idx = text.find("{")
    if idx == -1:
        return text
    # find matching closing brace
    depth = 0
    in_str = False
    escape = False
    for i in range(idx, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[idx : i + 1]
    # fallback: return everything from { to last }
    last_brace = text.rfind("}")
    if last_brace > idx:
        return text[idx : last_brace + 1]
    return text[idx:]


def _repair_json(text: str) -> str:
    """尝试修复格式错误的 JSON（不改变业务内容）。"""
    text = text.strip()
    # strip markdown
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # find first {
    idx = text.find("{")
    if idx != -1:
        text = text[idx:]
    # find last }
    last_brace = text.rfind("}")
    if last_brace != -1:
        candidate = text[: last_brace + 1]
        candidate = _clean_trailing_commas(candidate)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    # close unclosed brackets
    opens: list[str] = []
    in_str = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ("{", "["):
            opens.append(ch)
        elif ch == "}":
            if opens and opens[-1] == "{":
                opens.pop()
        elif ch == "]":
            if opens and opens[-1] == "[":
                opens.pop()
    closers = {"[": "]", "{": "}"}
    for opener in reversed(opens):
        text += closers.get(opener, "")
    text = _clean_trailing_commas(text)
    return text


def _clean_trailing_commas(text: str) -> str:
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    return text


def _parse_model_json(raw_text: str, error_log_path: Path | None = None) -> dict:
    """解析模型 JSON 输出，失败时自动 repair 一次。"""
    # attempt 1: extract JSON object
    extracted = _extract_json_object(raw_text)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass
    # attempt 2: repair
    repaired = _repair_json(extracted)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        if error_log_path:
            error_log_path.parent.mkdir(parents=True, exist_ok=True)
            error_log_path.write_text(
                json.dumps(
                    {"error": str(e), "original_preview": raw_text[:3000], "repaired_preview": repaired[:3000]},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
        raise ValueError(f"JSON 解析失败（repair 后仍失败）: {e}")


# ─── Ingestion validation ────────────────────────────────────────────────────

VALID_EVIDENCE_STRENGTHS = {"direct_observed", "context_supported", "inferred", "uncertain"}
VALID_ELEMENT_TYPES = {
    "strategy", "visual_tactic", "product", "people", "scene", "prop", "action",
    "text_speech", "selling_point", "proof", "offer", "emotion", "other",
}
VALID_FRAME_ROLES = {
    "visual_tactic_evidence", "offer_evidence", "pain_evidence",
    "product_evidence", "result_evidence", "generic_talking_head",
}
FORBIDDEN_FIELDS = {"confidence", "source_type", "clip_path", "clip.mp4", "start_sec", "end_sec"}


def _validate_global_analysis(data: dict) -> tuple[str, list[str]]:
    """校验 global_analysis.json，返回 (status, warnings)。"""
    warnings: list[str] = []

    # 检查必要字段
    if "video_record" not in data:
        return "fail", ["video_record 缺失"]
    if "module_records" not in data:
        return "fail", ["module_records 缺失"]
    if "raw_element_mentions" not in data:
        return "fail", ["raw_element_mentions 缺失"]
    if "frame_requests" not in data:
        return "fail", ["frame_requests 缺失"]

    # 检查 module_records 数量
    modules = data.get("module_records", [])
    if len(modules) < 3:
        warnings.append(f"module_records 数量过少: {len(modules)} < 3")
    if len(modules) > 12:
        warnings.append(f"module_records 数量过多: {len(modules)} > 12")

    # 检查 raw_element_mentions 不为空
    mentions = data.get("raw_element_mentions", [])
    if not mentions:
        warnings.append("raw_element_mentions 为空")

    # 检查 frame_requests 不为空
    frame_requests = data.get("frame_requests", [])
    if not frame_requests:
        warnings.append("frame_requests 为空")

    # 检查 frame_requests 不超过 12
    if len(frame_requests) > 12:
        warnings.append(f"frame_requests 数量过多: {len(frame_requests)} > 12，将截断")

    # 检查禁用字段
    data_str = json.dumps(data)
    forbidden_found = []
    for field in FORBIDDEN_FIELDS:
        if field in data_str:
            forbidden_found.append(field)
            warnings.append(f"发现禁用字段: {field}")

    # 检查 evidence_strength
    for mention in mentions:
        strength = mention.get("evidence_strength", "")
        if strength and strength not in VALID_EVIDENCE_STRENGTHS:
            warnings.append(f"invalid evidence_strength: {strength}")

    # 检查 element_type
    for mention in mentions:
        etype = mention.get("element_type", "")
        if etype and etype not in VALID_ELEMENT_TYPES:
            warnings.append(f"invalid element_type: {etype}")

    # 检查 visual_tactic 是否存在
    has_visual_tactic = any(m.get("element_type") == "visual_tactic" for m in mentions)
    if not has_visual_tactic:
        warnings.append("raw_element_mentions 中缺少 visual_tactic 类型")

    # 检查引用关系
    module_ids = {m.get("module_id") for m in data.get("module_records", [])}
    mention_ids = {m.get("mention_id") for m in mentions}

    # 检查 raw_element_mentions.module_id
    for mention in mentions:
        mid = mention.get("module_id", "")
        if mid and mid not in module_ids:
            warnings.append(f"raw_element_mentions.module_id 不存在: {mid}")

    # 检查 frame_requests.module_id
    for req in data.get("frame_requests", []):
        mid = req.get("module_id", "")
        if mid and mid not in module_ids:
            warnings.append(f"frame_requests.module_id 不存在: {mid}")

    # 检查 frame_requests.related_mentions
    for req in data.get("frame_requests", []):
        for rid in req.get("related_mentions", []):
            if rid and rid not in mention_ids:
                warnings.append(f"frame_requests.related_mentions 不存在: {rid}")

    # 检查 transfer_pattern_records.source_modules
    for pattern in data.get("transfer_pattern_records", []):
        for mid in pattern.get("source_modules", []):
            if mid and mid not in module_ids:
                warnings.append(f"transfer_pattern_records.source_modules 不存在: {mid}")

    # 检查 transfer_pattern_records.source_mentions
    for pattern in data.get("transfer_pattern_records", []):
        for rid in pattern.get("source_mentions", []):
            if rid and rid not in mention_ids:
                warnings.append(f"transfer_pattern_records.source_mentions 不存在: {rid}")

    # 判断 status
    has_critical = any("缺失" in w for w in warnings) or forbidden_found or not has_visual_tactic
    status = "fail" if has_critical else "pass"
    return status, warnings


# ─── Keyframe deduplication ──────────────────────────────────────────────────

FRAME_ROLE_PRIORITY = {
    "visual_tactic_evidence": 0,
    "offer_evidence": 1,
    "pain_evidence": 1,
    "product_evidence": 1,
    "result_evidence": 1,
    "generic_talking_head": 2,
}


def _deduplicate_frame_requests(frame_requests: list[dict], max_frames: int = 10) -> list[dict]:
    """对 frame_requests 进行去重和优先级筛选。"""
    if not frame_requests:
        return []

    # 按 module_id 分组
    by_module: dict[str, list[dict]] = {}
    for req in frame_requests:
        mid = req.get("module_id", "")
        by_module.setdefault(mid, []).append(req)

    result: list[dict] = []

    for mid, reqs in by_module.items():
        # 按 timestamp_sec 排序
        reqs.sort(key=lambda x: x.get("timestamp_sec", 0))

        # 每个 module 最多保留 2 张
        module_result: list[dict] = []
        for req in reqs:
            # 检查时间间隔
            if module_result:
                last_ts = module_result[-1].get("timestamp_sec", 0)
                curr_ts = req.get("timestamp_sec", 0)
                if abs(curr_ts - last_ts) < 2:
                    # 时间间隔 < 2 秒，只保留优先级更高的
                    last_priority = FRAME_ROLE_PRIORITY.get(module_result[-1].get("frame_role", ""), 2)
                    curr_priority = FRAME_ROLE_PRIORITY.get(req.get("frame_role", ""), 2)
                    if curr_priority < last_priority:
                        module_result[-1] = req
                    continue

            module_result.append(req)
            if len(module_result) >= 2:
                break

        result.extend(module_result)

    # 按优先级排序，截断到 max_frames
    result.sort(key=lambda x: FRAME_ROLE_PRIORITY.get(x.get("frame_role", ""), 2))
    return result[:max_frames]


# ─── ffmpeg operations ──────────────────────────────────────────────────────

def _ffmpeg_extract_keyframe(video_path: Path, timestamp: float, out_path: Path) -> bool:
    """ffmpeg 抽取关键帧。"""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error(f"ffmpeg 抽关键帧失败: {result.stderr[-300:]}")
        return False
    return out_path.exists()


# ─── records builders ────────────────────────────────────────────────────────

def _build_video_record(data: dict, video_id: str, duration: float) -> dict:
    """构建 video_record.jsonl 记录。"""
    vr = data.get("video_record", {})
    return {
        "video_id": video_id,
        "observed_brand_or_product_text": vr.get("observed_brand_or_product_text", ""),
        "product_category": vr.get("product_category", ""),
        "main_product": vr.get("main_product", ""),
        "duration_sec": duration,
        "language": vr.get("language", "zh"),
        "overall_strategy_summary": vr.get("overall_strategy_summary", ""),
        "strategy_pattern": vr.get("strategy_pattern", ""),
        "target_audience": vr.get("target_audience", []),
        "main_pain_points": vr.get("main_pain_points", []),
        "main_selling_points": vr.get("main_selling_points", []),
        "main_offer": vr.get("main_offer", ""),
        "main_visual_tactics": vr.get("main_visual_tactics", []),
        "creative_summary_for_generation": vr.get("creative_summary_for_generation", ""),
        "created_by": "global_agent",
        "schema_version": "competitor_global_image_v1",
    }


def _build_module_record(module: dict, video_id: str) -> dict:
    """构建 module_record.jsonl 记录。"""
    return {
        "module_id": module.get("module_id", ""),
        "video_id": video_id,
        "module_name": module.get("module_name", ""),
        "module_name_cn": module.get("module_name_cn", ""),
        "module_role": module.get("module_role", ""),
        "what_happens": module.get("what_happens", ""),
        "why_it_matters": module.get("why_it_matters", ""),
        "evidence_timestamps": module.get("evidence_timestamps", []),
        "key_text_or_speech": module.get("key_text_or_speech", []),
        "visual_tactics_summary": module.get("visual_tactics_summary", []),
        "module_summary_for_generation": module.get("module_summary_for_generation", ""),
    }


def _build_element_mention_record(mention: dict, video_id: str) -> dict:
    """构建 raw_element_mention.jsonl 记录。"""
    return {
        "mention_id": mention.get("mention_id", ""),
        "video_id": video_id,
        "module_id": mention.get("module_id", ""),
        "element_type": mention.get("element_type", ""),
        "raw_description": mention.get("raw_description", ""),
        "tentative_name": mention.get("tentative_name", ""),
        "tentative_name_cn": mention.get("tentative_name_cn", ""),
        "new_candidate": mention.get("new_candidate", ""),
        "evidence_source": mention.get("evidence_source", ""),
        "evidence_text": mention.get("evidence_text", ""),
        "evidence_timestamps": mention.get("evidence_timestamps", []),
        "evidence_strength": mention.get("evidence_strength", "uncertain"),
        "role_in_module": mention.get("role_in_module", ""),
        "generation_value": mention.get("generation_value", ""),
        "notes": mention.get("notes", ""),
    }


def _build_frame_request_record(req: dict, video_id: str) -> dict:
    """构建 frame_request.jsonl 记录。"""
    return {
        "frame_request_id": req.get("frame_request_id", ""),
        "video_id": video_id,
        "module_id": req.get("module_id", ""),
        "timestamp_sec": req.get("timestamp_sec", 0),
        "frame_role": req.get("frame_role", ""),
        "what_to_capture": req.get("what_to_capture", ""),
        "visual_tactic": req.get("visual_tactic", ""),
        "why_this_frame": req.get("why_this_frame", ""),
        "avoid_similar_reason": req.get("avoid_similar_reason", ""),
        "related_mentions": req.get("related_mentions", []),
    }


def _build_frame_record(
    req: dict, video_id: str, image_path: str,
) -> dict:
    """构建 frame_record.jsonl 记录。"""
    return {
        "frame_id": f"{video_id}_{req.get('frame_request_id', '')}",
        "video_id": video_id,
        "module_id": req.get("module_id", ""),
        "frame_request_id": req.get("frame_request_id", ""),
        "timestamp_sec": req.get("timestamp_sec", 0),
        "image_path": image_path,
        "frame_role": req.get("frame_role", ""),
        "what_it_shows": req.get("what_to_capture", ""),
        "visual_tactic": req.get("visual_tactic", ""),
        "related_mentions": req.get("related_mentions", []),
    }


def _build_transfer_pattern_record(pattern: dict, video_id: str) -> dict:
    """构建 transfer_pattern_record.jsonl 记录。"""
    return {
        "pattern_id": pattern.get("pattern_id", ""),
        "video_id": video_id,
        "pattern_type": pattern.get("pattern_type", ""),
        "pattern_name": pattern.get("pattern_name", ""),
        "pattern_name_cn": pattern.get("pattern_name_cn", ""),
        "description": pattern.get("description", ""),
        "source_modules": pattern.get("source_modules", []),
        "source_mentions": pattern.get("source_mentions", []),
        "transferability": pattern.get("transferability", ""),
        "how_to_adapt_for_own_brand": pattern.get("how_to_adapt_for_own_brand", ""),
        "non_transferable_parts": pattern.get("non_transferable_parts", []),
    }


# ─── Main pipeline ───────────────────────────────────────────────────────────

class CompetitorGlobalPipeline:
    """竞品广告全局分析管线：Global Agent → global_analysis → 校验 → 抽关键帧 → records"""

    def __init__(self) -> None:
        pass

    def run(
        self,
        video_id: str,
        video_url: str | None,
        video_path: str | None,
        output_dir: str,
        model: str | None = None,
    ) -> dict:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        records_dir = out / "records"
        records_dir.mkdir(exist_ok=True)
        keyframes_dir = out / "keyframes"
        keyframes_dir.mkdir(exist_ok=True)
        logs_dir = out / "logs"
        logs_dir.mkdir(exist_ok=True)

        setup_logger(__name__, str(out))
        config = Config.from_env(model_override=model)
        client = BailianClient(config)

        prompt = (
            Path(__file__).parent.parent / "prompts" / "competitor_global_image_analysis.md"
        ).read_text(encoding="utf-8")

        # ── Step 1: 调用模型 ──
        logger.info(f"[CompetitorGlobal] 调用模型分析视频: {video_id}")
        messages = client.build_video_message(prompt, video_url=video_url, video_path=video_path)
        raw_text = client._call_model(messages)

        # 保存 raw response
        raw_path = out / "analysis_raw.json"
        save_json({"raw_response": raw_text}, raw_path)

        # ── Step 2: JSON 解析 ──
        logger.info("[CompetitorGlobal] 解析模型输出 JSON...")
        try:
            global_analysis = _parse_model_json(
                raw_text, error_log_path=logs_dir / "debug_parse_failed.txt"
            )
        except ValueError as e:
            logger.error(f"JSON 解析失败: {e}")
            self._save_fail_outputs(out, video_id, str(e))
            return {"status": "fail", "reason": str(e), "output_dir": str(out)}

        # ── Step 3: ffprobe 获取真实时长 ──
        actual_duration = None
        if video_path and Path(video_path).exists():
            actual_duration = _ffprobe_duration(video_path)
            if actual_duration:
                logger.info(f"[CompetitorGlobal] ffprobe 时长: {actual_duration:.2f}s")
                # 用真实时长覆盖模型值
                if "video_record" in global_analysis:
                    global_analysis["video_record"]["duration_sec"] = actual_duration

        # ── Step 4: 校验 ──
        status, warnings = _validate_global_analysis(global_analysis)
        
        # ── Step 5: 去重 frame_requests ──
        frame_requests = global_analysis.get("frame_requests", [])
        frame_requests = _deduplicate_frame_requests(frame_requests, max_frames=10)
        global_analysis["frame_requests"] = frame_requests
        logger.info(f"[CompetitorGlobal] 去重后 frame_requests: {len(frame_requests)}")

        # ── Step 6: 抽取关键帧 ──
        video_path_obj = Path(video_path) if video_path else None
        frame_records: list[dict] = []
        extraction_warnings: list[str] = []
        frame_index = 0

        for req in frame_requests:
            module_id = req.get("module_id", "unknown")
            frame_request_id = req.get("frame_request_id", "")
            timestamp = req.get("timestamp_sec", 0)

            # 创建 module 子目录
            module_dir = keyframes_dir / _safe_slug(module_id)
            module_dir.mkdir(parents=True, exist_ok=True)

            # 生成安全文件名（顺序编号）
            frame_index += 1
            frame_filename = f"frame_{frame_index:03d}.jpg"
            frame_path = module_dir / frame_filename
            relative_path = f"keyframes/{_safe_slug(module_id)}/{frame_filename}"

            # 抽帧
            if video_path_obj and video_path_obj.exists():
                ok = _ffmpeg_extract_keyframe(video_path_obj, timestamp, frame_path)
                if not ok:
                    extraction_warnings.append(f"抽帧失败: {frame_request_id}")
                    continue
            else:
                extraction_warnings.append(f"无本地视频，跳过抽帧: {frame_request_id}")
                continue

            # 构建 frame_record
            frame_records.append(_build_frame_record(req, video_id, relative_path))

        logger.info(f"[CompetitorGlobal] 成功抽取 {len(frame_records)} 张关键帧")

        # ── Step 7: 写回 warnings 到 global_analysis ──
        if "ingestion_status" not in global_analysis:
            global_analysis["ingestion_status"] = {}
        global_analysis["ingestion_status"]["status"] = status
        global_analysis["ingestion_status"]["warnings"] = warnings
        global_analysis["ingestion_status"]["extraction_warnings"] = extraction_warnings

        # 保存 global_analysis.json（在去重和抽帧之后）
        save_json(global_analysis, out / "global_analysis.json")
        logger.info(f"[CompetitorGlobal] ingestion_status: {status}")

        if status == "fail":
            logger.error(f"[CompetitorGlobal] 校验失败: {warnings}")
            self._save_fail_outputs(out, video_id, "; ".join(warnings), global_analysis)
            return {
                "status": "fail",
                "reason": "; ".join(warnings),
                "global_analysis_path": str(out / "global_analysis.json"),
                "output_dir": str(out),
            }

        # ── Step 8: 生成 records ──
        # 使用 actual_duration 或 global_analysis.video_record.duration_sec 或 0
        video_record_duration = actual_duration
        if video_record_duration is None and "video_record" in global_analysis:
            video_record_duration = global_analysis["video_record"].get("duration_sec")
        video_record = _build_video_record(global_analysis, video_id, video_record_duration or 0)
        self._write_jsonl(records_dir / "video_record.jsonl", [video_record])

        module_records = [_build_module_record(m, video_id) for m in global_analysis.get("module_records", [])]
        self._write_jsonl(records_dir / "module_record.jsonl", module_records)

        element_mentions = [_build_element_mention_record(m, video_id) for m in global_analysis.get("raw_element_mentions", [])]
        self._write_jsonl(records_dir / "raw_element_mention.jsonl", element_mentions)

        frame_request_records = [_build_frame_request_record(r, video_id) for r in frame_requests]
        self._write_jsonl(records_dir / "frame_request.jsonl", frame_request_records)

        self._write_jsonl(records_dir / "frame_record.jsonl", frame_records)

        transfer_patterns = [_build_transfer_pattern_record(p, video_id) for p in global_analysis.get("transfer_pattern_records", [])]
        self._write_jsonl(records_dir / "transfer_pattern_record.jsonl", transfer_patterns)

        # ── Step 9: final_result.json ──
        # 检查是否有 visual_tactic
        has_visual_tactic = any(m.get("element_type") == "visual_tactic" for m in global_analysis.get("raw_element_mentions", []))
        
        final_result = {
            "video_id": video_id,
            "status": "pass",
            "global_analysis_path": "global_analysis.json",
            "records_dir": "records",
            "keyframes_dir": "keyframes",
            "module_count": len(module_records),
            "raw_element_mention_count": len(element_mentions),
            "frame_request_count": len(frame_requests),
            "frames_extracted": len(frame_records),
            "transfer_pattern_count": len(transfer_patterns),
            "has_visual_tactic": has_visual_tactic,
            "warnings": warnings + extraction_warnings,
            "summary": global_analysis.get("video_record", {}).get("overall_strategy_summary", ""),
        }
        save_json(final_result, out / "final_result.json")

        # ── 摘要 ──
        logger.info(
            f"[CompetitorGlobal] 完成 | modules={len(module_records)} | "
            f"mentions={len(element_mentions)} | frames={len(frame_records)} | "
            f"patterns={len(transfer_patterns)} | status=pass"
        )

        return {
            "status": "pass",
            "video_id": video_id,
            "module_count": len(module_records),
            "raw_element_mention_count": len(element_mentions),
            "frame_count": len(frame_records),
            "transfer_pattern_count": len(transfer_patterns),
            "output_dir": str(out),
        }

    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _save_fail_outputs(
        self,
        out: Path,
        video_id: str,
        reason: str,
        global_analysis: dict | None = None,
    ) -> None:
        if global_analysis:
            save_json(global_analysis, out / "global_analysis.json")
        # minimal final_result
        save_json({
            "video_id": video_id,
            "status": "fail",
            "reason": reason,
            "global_analysis_path": "global_analysis.json" if global_analysis else "",
        }, out / "final_result.json")
