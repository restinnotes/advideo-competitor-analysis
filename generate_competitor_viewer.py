#!/usr/bin/env python3
"""生成竞品广告分析结果展示网页"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).parent
    outputs_dir = project_root / "outputs"
    template_path = project_root / "competitor_viewer.html"
    output_path = project_root / "competitor_viewer.html"

    results: dict[str, dict] = {}

    for video_dir in sorted(outputs_dir.iterdir()):
        if not video_dir.is_dir():
            continue
        
        # 查找嵌套的视频目录
        for nested_dir in video_dir.iterdir():
            if not nested_dir.is_dir():
                continue
            
            final_path = nested_dir / "final_result.json"
            global_analysis_path = nested_dir / "global_analysis.json"
            frame_record_path = nested_dir / "records" / "frame_record.jsonl"
            
            if final_path.exists():
                with open(final_path, "r", encoding="utf-8") as f:
                    final_result = json.load(f)
                
                global_analysis = {}
                if global_analysis_path.exists():
                    with open(global_analysis_path, "r", encoding="utf-8") as f:
                        global_analysis = json.load(f)
                
                frame_records = []
                if frame_record_path.exists():
                    with open(frame_record_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                frame_records.append(json.loads(line))
                
                results[nested_dir.name] = {
                    "final_result": final_result,
                    "global_analysis": global_analysis,
                    "frame_records": frame_records
                }

    template = template_path.read_text(encoding="utf-8")
    results_json = json.dumps(results, ensure_ascii=False, indent=2)
    final_html = template.replace("RESULTS_DATA_PLACEHOLDER", results_json)
    output_path.write_text(final_html, encoding="utf-8")
    print(f"生成网页: {output_path}")
    print(f"包含 {len(results)} 个视频结果")


if __name__ == "__main__":
    main()