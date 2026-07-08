#!/usr/bin/env python3
"""生成结果展示网页"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).parent
    outputs_dir = project_root / "outputs"
    template_path = project_root / "viewer.html"
    output_path = project_root / "viewer.html"

    results: dict[str, dict] = {}

    for video_dir in sorted(outputs_dir.iterdir()):
        if not video_dir.is_dir():
            continue
        final_path = video_dir / "final_result.json"
        if final_path.exists():
            with open(final_path, "r", encoding="utf-8") as f:
                results[video_dir.name] = json.load(f)

    template = template_path.read_text(encoding="utf-8")
    results_json = json.dumps(results, ensure_ascii=False, indent=2)
    final_html = template.replace("RESULTS_DATA_PLACEHOLDER", results_json)
    output_path.write_text(final_html, encoding="utf-8")
    print(f"生成网页: {output_path}")
    print(f"包含 {len(results)} 个视频结果")


if __name__ == "__main__":
    main()
