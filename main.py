#!/usr/bin/env python3
"""广告短视频语义 clip 资产管线"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.video_analyzer import VideoAnalyzer
from src.global_element_pipeline import GlobalElementPipeline
from src.competitor_global_pipeline import CompetitorGlobalPipeline


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="广告短视频语义 clip 资产管线 - Qwen-Omni")
    parser.add_argument("action", choices=["analyze", "global_elements", "competitor_image_analysis"])
    parser.add_argument("--video-id", required=True, help="视频唯一标识")
    parser.add_argument("--video-url", help="公网视频 URL（百炼模型用）")
    parser.add_argument("--video-path", help="本地视频路径（ffmpeg 切 clip/keyframe 用）")
    parser.add_argument("--output-dir", default="./outputs", help="输出目录（默认 ./outputs）")
    parser.add_argument("--model", help="qwen3.5-omni-plus 或 qwen3.5-omni-flash")
    args = parser.parse_args()

    if not args.video_url:
        print("错误: 必须提供 --video-url", file=sys.stderr)
        return 1

    out = Path(args.output_dir) / args.video_id

    try:
        if args.action == "analyze":
            result = VideoAnalyzer().analyze(
                video_id=args.video_id,
                video_url=args.video_url,
                video_path=args.video_path,
                output_dir=str(out),
                model=args.model,
            )
            clip_count = len(result.get("clip_outputs", []))
            print(f"完成! 输出: {out}")
            print(f"Semantic clips: {clip_count} 个")
        elif args.action == "global_elements":
            result = GlobalElementPipeline().run(
                video_id=args.video_id,
                video_url=args.video_url,
                video_path=args.video_path,
                output_dir=str(out),
                model=args.model,
            )
            if result["status"] == "pass":
                print(f"\nGlobal element pipeline finished")
                print(f"video_id: {result['video_id']}")
                print(f"duration_sec: {result['duration_sec']}")
                print(f"clip_count: {result['clip_count']}")
                print(f"coverage_ratio: {result['coverage_ratio']}")
                print(f"element_mentions: {result['element_mentions']}")
                print(f"status: pass")
                print(f"output_dir: {result['output_dir']}")
            else:
                print(f"\nGlobal element pipeline failed")
                print(f"reason: {result['reason']}")
                if "shared_memory_path" in result:
                    print(f"shared_memory_path: {result['shared_memory_path']}")
                if "ingestion_status_path" in result:
                    print(f"ingestion_status_path: {result['ingestion_status_path']}")
                return 1
        elif args.action == "competitor_image_analysis":
            result = CompetitorGlobalPipeline().run(
                video_id=args.video_id,
                video_url=args.video_url,
                video_path=args.video_path,
                output_dir=str(out),
                model=args.model,
            )
            if result["status"] == "pass":
                print(f"\nCompetitor image analysis finished")
                print(f"video_id: {result['video_id']}")
                print(f"module_count: {result['module_count']}")
                print(f"raw_element_mentions: {result['raw_element_mention_count']}")
                print(f"frame_requests: {result['frame_count']}")
                print(f"frames_extracted: {result['frame_count']}")
                print(f"transfer_patterns: {result['transfer_pattern_count']}")
                print(f"output_dir: {result['output_dir']}")
            else:
                print(f"\nCompetitor image analysis failed")
                print(f"reason: {result['reason']}")
                if "global_analysis_path" in result:
                    print(f"global_analysis_path: {result['global_analysis_path']}")
                return 1
        return 0
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
