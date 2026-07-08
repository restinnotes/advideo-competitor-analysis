"""Global Element Pipeline - 全局视频理解 Agent + 程序切片"""

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
    """从 clip_title 或 primary_strategy_element 生成安全文件名片段。"""
    s = text.lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s or "clip"


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
    "strategy", "product", "people", "scene", "prop", "action",
    "text_speech", "selling_point", "proof", "offer", "visual_style",
    "emotion", "other",
}


def _validate_timeline(timeline: list[dict]) -> list[str]:
    """校验 timeline，返回 warning 列表。"""
    warnings: list[str] = []
    if not timeline:
        return warnings
    for i, clip in enumerate(timeline):
        s = clip.get("start_sec", 0)
        e = clip.get("end_sec", 0)
        if e <= s:
            warnings.append(f"clip_{i+1}: end_sec({e}) <= start_sec({s})")
        dur = e - s
        if dur < 0.5:
            warnings.append(f"clip_{i+1}: duration={dur:.2f}s < 0.5s")
        if dur > 12:
            warnings.append(f"clip_{i+1}: duration={dur:.2f}s > 12s")
        kf = clip.get("keyframe_timestamp_sec", (s + e) / 2)
        if kf < s or kf > e:
            warnings.append(f"clip_{i+1}: keyframe_timestamp={kf} not in [{s}, {e}]")
    # check gaps
    for i in range(1, len(timeline)):
        prev_end = timeline[i - 1].get("end_sec", 0)
        curr_start = timeline[i].get("start_sec", 0)
        gap = curr_start - prev_end
        if gap > 3:
            warnings.append(f"gap between clip_{i} and clip_{i+1}: {gap:.2f}s")
    return warnings


def _build_ingestion_status(
    shared_memory: dict,
    actual_duration: float | None,
) -> dict:
    """构建 ingestion_status.json。"""
    timeline = shared_memory.get("timeline", [])
    model_dur = shared_memory.get("video_profile", {}).get("estimated_duration_sec", 0) or 0
    max_end = max((c.get("end_sec", 0) for c in timeline), default=0)
    duration = actual_duration or model_dur

    coverage = max_end / duration if duration > 0 else 0

    blocking_errors: list[str] = []
    warnings: list[str] = []

    if not timeline:
        blocking_errors.append("timeline 为空")
    if coverage < 0.9:
        blocking_errors.append(f"coverage_ratio={coverage:.3f} < 0.9")

    # check time ordering
    for i in range(1, len(timeline)):
        if timeline[i].get("start_sec", 0) < timeline[i - 1].get("start_sec", 0):
            blocking_errors.append(f"clip 时间倒序: clip_{i+1}.start < clip_{i}.start")
            break

    # time validation warnings
    warnings.extend(_validate_timeline(timeline))

    # last clip distance from end
    if timeline and actual_duration:
        last_end = timeline[-1].get("end_sec", 0)
        dist = actual_duration - last_end
        if dist > 5 and coverage >= 0.9:
            warnings.append(f"最后一段距离视频结尾 {dist:.2f}s")

    # keyframe correction
    for clip in timeline:
        s = clip.get("start_sec", 0)
        e = clip.get("end_sec", 0)
        kf = clip.get("keyframe_timestamp_sec", 0)
        if kf < s or kf > e:
            mid = round((s + e) / 2, 2)
            clip["keyframe_timestamp_sec"] = mid
            warnings.append(f"{clip.get('clip_id', '?')}: keyframe corrected to {mid}")

    status = "fail" if blocking_errors else "pass"

    return {
        "status": status,
        "actual_duration_sec": actual_duration or 0,
        "model_estimated_duration_sec": model_dur,
        "max_timeline_end_sec": max_end,
        "coverage_ratio": round(coverage, 4),
        "clip_count": len(timeline),
        "blocking_errors": blocking_errors,
        "warnings": warnings,
    }


# ─── ffmpeg operations ──────────────────────────────────────────────────────

def _ffmpeg_cut_clip(video_path: Path, start: float, duration: float, out_path: Path) -> bool:
    """ffmpeg 切 clip.mp4。"""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error(f"ffmpeg 切 clip 失败: {result.stderr[-300:]}")
        return False
    return out_path.exists()


def _ffmpeg_extract_keyframe(video_path: Path, timestamp: float, out_path: Path) -> bool:
    """ffmpeg 抽取 keyframe.jpg。"""
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
        logger.error(f"ffmpeg 抽 keyframe 失败: {result.stderr[-300:]}")
        return False
    return out_path.exists()


# ─── records builders ────────────────────────────────────────────────────────

def _build_video_record(shared_memory: dict, video_id: str, duration: float, status: str) -> dict:
    vp = shared_memory.get("video_profile", {})
    gs = shared_memory.get("global_strategy", {})
    return {
        "video_id": video_id,
        "source_type": vp.get("source_type", "unknown"),
        "source_brand": vp.get("source_brand", ""),
        "product_category": vp.get("product_category", ""),
        "main_product": vp.get("main_product", ""),
        "duration_sec": duration,
        "global_strategy_summary": gs.get("brand_free_strategy_summary", ""),
        "strategy_chain": gs.get("strategy_chain", []),
        "target_audience": vp.get("target_audience", []),
        "main_pain_points": vp.get("main_pain_points", []),
        "main_selling_points": vp.get("main_selling_points", []),
        "main_offer": vp.get("main_offer", ""),
        "ingestion_status": status,
    }


def _build_clip_record(clip: dict, video_id: str) -> dict:
    return {
        "clip_id": clip.get("clip_id", ""),
        "video_id": video_id,
        "sequence_index": clip.get("sequence_index", 0),
        "start_sec": clip.get("start_sec", 0),
        "end_sec": clip.get("end_sec", 0),
        "duration_sec": round(clip.get("end_sec", 0) - clip.get("start_sec", 0), 2),
        "clip_path": f"clips/{_safe_clip_dir_name(clip)}/clip.mp4",
        "keyframe_path": f"clips/{_safe_clip_dir_name(clip)}/keyframe.jpg",
        "primary_strategy_element": clip.get("primary_strategy_element", ""),
        "visual_node_type": clip.get("visual_node_type", ""),
        "what_happens": clip.get("what_happens", ""),
        "persuasive_function": clip.get("persuasive_function", ""),
        "key_text_or_speech": clip.get("key_text_or_speech", ""),
    }


def _build_element_mention_record(
    mention: dict, clip: dict, video_id: str, mention_index: int,
) -> dict:
    clip_id = clip.get("clip_id", "")
    seq = clip.get("sequence_index", 0)
    return {
        "mention_id": f"{video_id}_{clip_id}_{mention_index:03d}",
        "video_id": video_id,
        "clip_id": clip_id,
        "sequence_index": seq,
        "element_type": mention.get("element_type", ""),
        "raw_description": mention.get("raw_description", ""),
        "normalized_name": mention.get("normalized_name", ""),
        "normalized_name_cn": mention.get("normalized_name_cn", ""),
        "new_candidate": mention.get("new_candidate", ""),
        "evidence_source": mention.get("evidence_source", ""),
        "evidence_text": mention.get("evidence_text", ""),
        "evidence_time_sec": mention.get("evidence_time_sec", 0),
        "role_in_clip": mention.get("role_in_clip", ""),
        "evidence_strength": mention.get("evidence_strength", "uncertain"),
        "notes": mention.get("notes", ""),
    }


def _safe_clip_dir_name(clip: dict) -> str:
    seq = clip.get("sequence_index", 0)
    slug = _safe_slug(
        clip.get("primary_strategy_element", "") or clip.get("clip_title", "") or "clip"
    )
    return f"{seq:02d}_clip_{seq:03d}_{slug}"


# ─── Main pipeline ───────────────────────────────────────────────────────────

class GlobalElementPipeline:
    """全局元素拆解管线：Global Agent → shared_memory → 校验 → ffmpeg 切片 → records"""

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
        clips_dir = out / "clips"
        clips_dir.mkdir(exist_ok=True)
        records_dir = out / "records"
        records_dir.mkdir(exist_ok=True)
        logs_dir = out / "logs"
        logs_dir.mkdir(exist_ok=True)

        setup_logger(__name__, str(out))
        config = Config.from_env(model_override=model)
        client = BailianClient(config)

        prompt = (
            Path(__file__).parent.parent / "prompts" / "global_element_agent.md"
        ).read_text(encoding="utf-8")

        # ── Step 1: 调用模型 ──
        logger.info(f"[GlobalElement] 调用模型分析视频: {video_id}")
        messages = client.build_video_message(prompt, video_url=video_url, video_path=video_path)
        raw_text = client._call_model(messages)

        # 保存 raw response
        raw_path = out / "analysis_raw.json"
        save_json({"raw_response": raw_text}, raw_path)

        # ── Step 2: JSON 解析 ──
        logger.info("[GlobalElement] 解析模型输出 JSON...")
        try:
            shared_memory = _parse_model_json(
                raw_text, error_log_path=logs_dir / "debug_parse_failed.txt"
            )
        except ValueError as e:
            logger.error(f"JSON 解析失败: {e}")
            self._save_fail_outputs(out, video_id, str(e))
            return {"status": "fail", "reason": str(e), "output_dir": str(out)}

        # ── Step 3: 保存 shared_memory.json ──
        save_json(shared_memory, out / "shared_memory.json")
        logger.info("[GlobalElement] shared_memory.json 已保存")

        # ── Step 4: ffprobe 获取真实时长 ──
        actual_duration = None
        if video_path and Path(video_path).exists():
            actual_duration = _ffprobe_duration(video_path)
            if actual_duration:
                logger.info(f"[GlobalElement] ffprobe 时长: {actual_duration:.2f}s")

        # ── Step 5: 校验 → ingestion_status ──
        ingestion_status = _build_ingestion_status(shared_memory, actual_duration)
        save_json(ingestion_status, out / "ingestion_status.json")
        logger.info(f"[GlobalElement] ingestion_status: {ingestion_status['status']}")

        if ingestion_status["status"] == "fail":
            logger.error(f"[GlobalElement] 校验失败: {ingestion_status['blocking_errors']}")
            self._save_fail_outputs(out, video_id, "ingestion_status=fail", shared_memory, ingestion_status)
            return {
                "status": "fail",
                "reason": "; ".join(ingestion_status["blocking_errors"]),
                "shared_memory_path": str(out / "shared_memory.json"),
                "ingestion_status_path": str(out / "ingestion_status.json"),
                "output_dir": str(out),
            }

        # ── Step 6: ffmpeg 切片 ──
        timeline = shared_memory.get("timeline", [])
        clip_records: list[dict] = []
        element_mentions_all: list[dict] = []
        clip_index_entries: list[dict] = []
        final_clips: list[dict] = []
        video_path_obj = Path(video_path) if video_path else None

        for clip in timeline:
            clip_id = clip.get("clip_id", "")
            seq = clip.get("sequence_index", 0)
            start = max(0.0, clip.get("start_sec", 0))
            end = clip.get("end_sec", 0)
            duration = round(end - start, 2)
            kf_ts = clip.get("keyframe_timestamp_sec", (start + end) / 2)

            if kf_ts < start or kf_ts > end:
                kf_ts = round((start + end) / 2, 2)
                clip["keyframe_timestamp_sec"] = kf_ts

            dir_name = _safe_clip_dir_name(clip)
            clip_dir = clips_dir / dir_name
            clip_dir.mkdir(parents=True, exist_ok=True)

            clip_ok = False
            kf_ok = False
            warnings: list[str] = []

            if video_path_obj and video_path_obj.exists():
                # cut clip
                clip_file = clip_dir / "clip.mp4"
                if duration > 0:
                    clip_ok = _ffmpeg_cut_clip(video_path_obj, start, duration, clip_file)
                    if not clip_ok:
                        warnings.append("ffmpeg cut clip failed")
                else:
                    warnings.append(f"duration={duration}s <= 0, skip clip cut")

                # extract keyframe
                kf_file = clip_dir / "keyframe.jpg"
                kf_ok = _ffmpeg_extract_keyframe(video_path_obj, kf_ts, kf_file)
                if not kf_ok:
                    warnings.append("ffmpeg extract keyframe failed")

            # clip_memory.json
            clip_memory = {
                "video_context": {
                    "main_product": shared_memory.get("video_profile", {}).get("main_product", ""),
                    "product_category": shared_memory.get("video_profile", {}).get("product_category", ""),
                    "brand_candidates": shared_memory.get("video_profile", {}).get("brand_candidates", []),
                    "target_audience": shared_memory.get("video_profile", {}).get("target_audience", []),
                    "main_pain_points": shared_memory.get("video_profile", {}).get("main_pain_points", []),
                    "main_selling_points": shared_memory.get("video_profile", {}).get("main_selling_points", []),
                    "main_offer": shared_memory.get("video_profile", {}).get("main_offer", ""),
                    "strategy_pattern_name": shared_memory.get("global_strategy", {}).get("strategy_pattern_name", ""),
                    "strategy_chain": shared_memory.get("global_strategy", {}).get("strategy_chain", []),
                },
                "current_clip": clip,
                "neighbor_context": {
                    "previous_clip_summary": timeline[seq - 2].get("what_happens", "") if seq >= 2 else "",
                    "next_clip_summary": timeline[seq].get("what_happens", "") if seq < len(timeline) else "",
                },
            }
            save_json(clip_memory, clip_dir / "clip_memory.json")

            # clip.json
            clip_json = {
                "clip_id": clip_id,
                "video_id": video_id,
                "sequence_index": seq,
                "start_sec": start,
                "end_sec": end,
                "duration_sec": duration,
                "clip_path": f"clips/{dir_name}/clip.mp4",
                "keyframe_path": f"clips/{dir_name}/keyframe.jpg",
                "clip_title": clip.get("clip_title", ""),
                "primary_strategy_element": clip.get("primary_strategy_element", ""),
                "secondary_strategy_elements": clip.get("secondary_strategy_elements", []),
                "visual_node_type": clip.get("visual_node_type", ""),
                "what_happens": clip.get("what_happens", ""),
                "key_text_or_speech": clip.get("key_text_or_speech", ""),
                "persuasive_function": clip.get("persuasive_function", ""),
                "brand_free_clip_text": clip.get("brand_free_clip_text", ""),
                "element_mentions": clip.get("element_mentions", []),
                "ingestion_status": {
                    "status": "pass" if clip_ok else "failed",
                    "warnings": warnings,
                },
            }
            save_json(clip_json, clip_dir / "clip.json")

            # clip_record.jsonl
            clip_records.append(_build_clip_record(clip, video_id))

            # element_mentions → element_mention.jsonl
            for mi, mention in enumerate(clip.get("element_mentions", [])):
                element_mentions_all.append(
                    _build_element_mention_record(mention, clip, video_id, mi + 1)
                )

            # clip_index entry
            clip_index_entries.append({
                "clip_id": clip_id,
                "sequence_index": seq,
                "start_sec": start,
                "end_sec": end,
                "duration_sec": duration,
                "clip_path": f"clips/{dir_name}/clip.mp4",
                "keyframe_path": f"clips/{dir_name}/keyframe.jpg",
                "clip_json_path": f"clips/{dir_name}/clip.json",
                "primary_strategy_element": clip.get("primary_strategy_element", ""),
                "clip_title": clip.get("clip_title", ""),
                "element_count": len(clip.get("element_mentions", [])),
            })

            # final_result entry
            final_clips.append({
                "clip_id": clip_id,
                "sequence_index": seq,
                "clip_path": f"clips/{dir_name}/clip.mp4",
                "keyframe_path": f"clips/{dir_name}/keyframe.jpg",
                "clip_json_path": f"clips/{dir_name}/clip.json",
                "primary_strategy_element": clip.get("primary_strategy_element", ""),
                "visual_node_type": clip.get("visual_node_type", ""),
                "element_count": len(clip.get("element_mentions", [])),
            })

        # ── Step 7: clip_index.json ──
        clip_index = {
            "video_id": video_id,
            "clip_count": len(clip_index_entries),
            "clips": clip_index_entries,
        }
        save_json(clip_index, out / "clip_index.json")

        # ── Step 8: final_result.json (轻量) ──
        duration_val = actual_duration or shared_memory.get("video_profile", {}).get("estimated_duration_sec", 0)
        final_result = {
            "video_id": video_id,
            "shared_memory_path": "shared_memory.json",
            "ingestion_status_path": "ingestion_status.json",
            "clip_index_path": "clip_index.json",
            "records_dir": "records",
            "clip_count": len(final_clips),
            "coverage_ratio": ingestion_status["coverage_ratio"],
            "clips": final_clips,
        }
        save_json(final_result, out / "final_result.json")

        # ── Step 9: records/*.jsonl ──
        self._write_jsonl(records_dir / "video_record.jsonl", [
            _build_video_record(shared_memory, video_id, duration_val, "pass")
        ])
        self._write_jsonl(records_dir / "clip_record.jsonl", clip_records)
        self._write_jsonl(records_dir / "element_mention.jsonl", element_mentions_all)

        # ── 摘要 ──
        total_mentions = len(element_mentions_all)
        logger.info(
            f"[GlobalElement] 完成 | clips={len(timeline)} | "
            f"coverage={ingestion_status['coverage_ratio']:.3f} | "
            f"element_mentions={total_mentions} | status=pass"
        )

        return {
            "status": "pass",
            "video_id": video_id,
            "duration_sec": duration_val,
            "clip_count": len(timeline),
            "coverage_ratio": ingestion_status["coverage_ratio"],
            "element_mentions": total_mentions,
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
        shared_memory: dict | None = None,
        ingestion_status: dict | None = None,
    ) -> None:
        if shared_memory:
            save_json(shared_memory, out / "shared_memory.json")
        if ingestion_status:
            save_json(ingestion_status, out / "ingestion_status.json")
        # minimal final_result
        save_json({
            "video_id": video_id,
            "status": "fail",
            "reason": reason,
            "shared_memory_path": "shared_memory.json" if shared_memory else "",
            "ingestion_status_path": "ingestion_status.json" if ingestion_status else "",
        }, out / "final_result.json")
