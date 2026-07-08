"""视频分析总控 - 语义 clip 资产版"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .bailian_client import BailianClient
from .clip_extractor import ClipExtractor
from .config import Config
from .json_utils import save_json
from .logging_utils import setup_logger
from .schemas import (
    ClipIndex,
    ClipIndexEntry,
    ClipOutput,
    FinalResult,
    VideoAnalysisResult,
    normalize_result,
)

logger = setup_logger(__name__)


class VideoAnalyzer:
    def __init__(self) -> None:
        self.extractor = ClipExtractor()

    def analyze(
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
        logs_dir = out / "logs"
        logs_dir.mkdir(exist_ok=True)

        setup_logger(__name__, str(out))
        config = Config.from_env(model_override=model)
        client = BailianClient(config)

        prompt = (
            Path(__file__).parent.parent / "prompts" / "video_analysis_prompt.txt"
        ).read_text(encoding="utf-8")

        # 1. 调用模型分析
        logger.info(f"分析视频: {video_id}")
        raw = client.analyze_video(
            prompt, video_url=video_url, video_path=video_path, save_dir=out
        )

        # 2. 保存 analysis_raw.json
        save_json(raw, out / "analysis_raw.json")

        # 3. 规范化
        analysis = normalize_result(raw)

        # 4. 保存 analysis_normalized.json
        save_json(analysis.model_dump(), out / "analysis_normalized.json")

        # 5. 切 clip 和 keyframe
        clip_outputs: list[ClipOutput] = []
        if video_path:
            vp = Path(video_path)
            if not vp.exists():
                logger.warning(f"本地视频不存在: {video_path}，跳过切 clip")
            else:
                for clip in analysis.semantic_clips:
                    dir_name = ClipExtractor.make_clip_dir_name(clip)
                    clip_dir = clips_dir / dir_name
                    clip_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        res = self.extractor.extract_clip_and_keyframe(vp, clip, clip_dir)
                        co = ClipOutput(
                            clip_id=clip.clip_id,
                            sequence_index=clip.sequence_index,
                            importance_rank=clip.importance_rank,
                            start_sec=clip.start_sec,
                            end_sec=clip.end_sec,
                            duration_sec=clip.duration_sec,
                            keyframe_timestamp_sec=clip.keyframe_timestamp_sec,
                            primary_strategy_stage=clip.primary_strategy_stage,
                            secondary_strategy_stages=clip.secondary_strategy_stages,
                            strategy_stage_detail=clip.strategy_stage_detail.model_dump(),
                            stage_position=clip.stage_position,
                            is_repeated_stage=clip.is_repeated_stage,
                            stage_repeat_index=clip.stage_repeat_index,
                            conversion_role=clip.conversion_role,
                            clip_title=clip.clip_title,
                            generic_strategy_label=clip.generic_strategy_label,
                            visual_node_type=clip.visual_node_type,
                            visual_node_detail=clip.visual_node_detail.model_dump(),
                            what_happens_visually=clip.what_happens_visually,
                            persuasive_function=clip.persuasive_function,
                            why_this_clip_exists=clip.why_this_clip_exists,
                            brand_free_strategy_description=clip.brand_free_strategy_description,
                            visual_elements=clip.visual_elements.model_dump(),
                            keyframe=clip.keyframe.model_dump(),
                            clustering_features=clip.clustering_features.model_dump(),
                            clip_path=res["clip_path"],
                            keyframe_path=res["keyframe_path"],
                            clip_json_path=res["clip_json_path"],
                            quality_flags=clip.quality_flags.model_dump(),
                        )
                        clip_outputs.append(co)
                    except Exception as e:
                        logger.error(f"切 clip 失败 {clip.clip_id}: {e}")

        # 6. 生成 clip_index.json
        clip_index = ClipIndex(
            video_id=video_id,
            model=config.model,
            clip_count=len(clip_outputs),
            clips=[
                ClipIndexEntry(
                    clip_id=co.clip_id,
                    sequence_index=co.sequence_index,
                    importance_rank=co.importance_rank,
                    primary_strategy_stage=co.primary_strategy_stage,
                    secondary_strategy_stages=co.secondary_strategy_stages,
                    visual_node_type=co.visual_node_type,
                    start_sec=co.start_sec,
                    end_sec=co.end_sec,
                    duration_sec=co.duration_sec,
                    keyframe_timestamp_sec=co.keyframe_timestamp_sec,
                    clip_path=co.clip_path,
                    keyframe_path=co.keyframe_path,
                    clip_json_path=co.clip_json_path,
                    clip_title=co.clip_title,
                    generic_strategy_label=co.generic_strategy_label,
                    brand_free_strategy_description=co.brand_free_strategy_description,
                    strategy_embedding_text=co.clustering_features.get("strategy_embedding_text", ""),
                    visual_embedding_text=co.clustering_features.get("visual_embedding_text", ""),
                    entity_embedding_text=co.clustering_features.get("entity_embedding_text", ""),
                )
                for co in clip_outputs
            ],
        )
        save_json(clip_index.model_dump(), out / "clip_index.json")

        # 7. 生成 final_result.json
        final = FinalResult(
            video_id=video_id,
            model=config.model,
            video_url=video_url or "",
            video_path=video_path or "",
            taxonomy_version=analysis.taxonomy_version,
            video_meta=analysis.video_meta.model_dump(),
            video_strategy=analysis.video_strategy.model_dump(),
            clip_outputs=[co.model_dump() for co in clip_outputs],
            video_level_tags=analysis.video_level_tags.model_dump(),
            video_clustering_features=analysis.video_clustering_features.model_dump(),
            quality_flags=analysis.quality_flags.model_dump(),
            created_at=datetime.now().isoformat(),
        )
        save_json(final.model_dump(), out / "final_result.json")

        logger.info(f"完成，共 {len(clip_outputs)} 个 semantic clip")
        return final.model_dump()
