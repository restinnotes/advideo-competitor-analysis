#!/usr/bin/env python3
"""验证竞品广告分析管线输出"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def verify_output_dir(output_dir: str) -> tuple[bool, list[str]]:
    """验证输出目录结构和内容。"""
    out = Path(output_dir)
    errors: list[str] = []
    warnings: list[str] = []

    # 检查必要文件
    required_files = [
        "global_analysis.json",
        "final_result.json",
        "records/video_record.jsonl",
        "records/module_record.jsonl",
        "records/raw_element_mention.jsonl",
        "records/frame_request.jsonl",
        "records/frame_record.jsonl",
        "records/transfer_pattern_record.jsonl",
    ]

    for f in required_files:
        if not (out / f).exists():
            errors.append(f"缺少文件: {f}")

    # 检查 global_analysis.json 结构
    ga_path = out / "global_analysis.json"
    if ga_path.exists():
        try:
            ga = json.loads(ga_path.read_text(encoding="utf-8"))

            # 检查顶层字段
            required_fields = ["schema_version", "video_record", "module_records", "raw_element_mentions", "frame_requests", "transfer_pattern_records", "ingestion_status"]
            for field in required_fields:
                if field not in ga:
                    errors.append(f"global_analysis.json 缺少字段: {field}")

            # 检查 schema_version
            if ga.get("schema_version") != "competitor_global_image_v1":
                warnings.append(f"schema_version 不匹配: {ga.get('schema_version')}")

            # 检查禁用字段
            ga_str = json.dumps(ga)
            forbidden_fields = ["confidence", "source_type", "clip_path", "clip.mp4", "start_sec", "end_sec"]
            for field in forbidden_fields:
                if field in ga_str:
                    errors.append(f"发现禁用字段: {field}")

            # 检查 module_records 数量
            modules = ga.get("module_records", [])
            if len(modules) < 3:
                warnings.append(f"module_records 数量过少: {len(modules)} < 3")
            if len(modules) > 12:
                warnings.append(f"module_records 数量过多: {len(modules)} > 12")

            # 检查 raw_element_mentions 不为空
            mentions = ga.get("raw_element_mentions", [])
            if not mentions:
                warnings.append("raw_element_mentions 为空")

            # 检查 frame_requests 不为空
            frame_requests = ga.get("frame_requests", [])
            if not frame_requests:
                warnings.append("frame_requests 为空")

            # 检查 frame_requests 不超过 12
            if len(frame_requests) > 12:
                warnings.append(f"frame_requests 数量过多: {len(frame_requests)} > 12")

            # 检查 visual_tactic 是否存在
            has_visual_tactic = any(m.get("element_type") == "visual_tactic" for m in mentions)
            if not has_visual_tactic:
                warnings.append("raw_element_mentions 中缺少 visual_tactic 类型")

            # 检查 video_record
            vr = ga.get("video_record", {})
            if not vr.get("video_id"):
                warnings.append("video_record.video_id 为空")

        except json.JSONDecodeError as e:
            errors.append(f"global_analysis.json JSON 解析失败: {e}")

    # 检查 final_result.json
    fr_path = out / "final_result.json"
    if fr_path.exists():
        try:
            fr = json.loads(fr_path.read_text(encoding="utf-8"))
            # 检查不包含 base64
            fr_str = json.dumps(fr)
            if "base64" in fr_str.lower():
                errors.append("final_result.json 包含 base64")
        except json.JSONDecodeError as e:
            errors.append(f"final_result.json JSON 解析失败: {e}")

    # 检查 keyframes 目录
    keyframes_dir = out / "keyframes"
    if keyframes_dir.exists():
        jpg_files = list(keyframes_dir.rglob("*.jpg"))
        if not jpg_files:
            warnings.append("keyframes 目录下没有 jpg 文件")
        else:
            print(f"  关键帧数量: {len(jpg_files)}")
    else:
        warnings.append("keyframes 目录不存在")

    # 检查不应该存在的文件
    forbidden_files = [
        "shared_memory.json",
        "clip_index.json",
        "ingestion_status.json",
    ]
    for f in forbidden_files:
        if (out / f).exists():
            warnings.append(f"存在不应该生成的文件: {f}")

    # 检查不应该存在的目录
    if (out / "clips").exists():
        warnings.append("存在 clips 目录（不应该生成 clip.mp4）")

    # 检查 JSONL 文件格式
    jsonl_files = [
        "records/video_record.jsonl",
        "records/module_record.jsonl",
        "records/raw_element_mention.jsonl",
        "records/frame_request.jsonl",
        "records/frame_record.jsonl",
        "records/transfer_pattern_record.jsonl",
    ]
    for f in jsonl_files:
        fpath = out / f
        if fpath.exists():
            try:
                lines = fpath.read_text(encoding="utf-8").strip().split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{f} 第 {i+1} 行 JSON 解析失败: {e}")

    # 检查 POSIX 路径
    if ga_path.exists():
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        fr_records = ga.get("frame_requests", [])
        for req in fr_records:
            # frame_requests 不应该包含文件路径
            pass

    # 检查 frame_record.jsonl 中的路径
    fr_path = out / "records" / "frame_record.jsonl"
    if fr_path.exists():
        lines = fr_path.read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            if line.strip():
                rec = json.loads(line)
                img_path = rec.get("image_path", "")
                if "\\" in img_path:
                    errors.append(f"frame_record.jsonl 包含 Windows 反斜杠路径: {img_path}")

    return len(errors) == 0, errors + warnings


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python verify_competitor_outputs.py <output_dir>")
        return 1

    output_dir = sys.argv[1]
    print(f"验证输出目录: {output_dir}")

    ok, messages = verify_output_dir(output_dir)

    for msg in messages:
        if msg.startswith("缺少文件") or msg.startswith("发现禁用字段") or "失败" in msg:
            print(f"  [ERROR] {msg}")
        else:
            print(f"  [WARN] {msg}")

    if ok:
        print("\n验证通过!")
        return 0
    else:
        print("\n验证失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
