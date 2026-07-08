"""语义 clip 提取器 - ffmpeg 切 clip 和 keyframe"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .filename_utils import safe_filename
from .logging_utils import setup_logger
from .schemas import SemanticClip

logger = setup_logger(__name__)


class ClipExtractor:
    """从原视频中切出 semantic clip 和对应 keyframe。"""

    def extract_clip_and_keyframe(
        self,
        video_path: Path,
        semantic_clip: SemanticClip,
        clip_dir: Path,
    ) -> dict:
        """切出一个 semantic clip 的 clip.mp4、keyframe.jpg、clip.json。

        Args:
            video_path: 原视频路径
            semantic_clip: 语义 clip 对象
            clip_dir: 该 clip 的输出文件夹（已创建）

        Returns:
            dict with clip_path, keyframe_path, clip_json_path

        Raises:
            RuntimeError: ffmpeg 失败时
            ValueError: 时间参数非法时
        """
        start = max(0.0, semantic_clip.start_sec)
        end = semantic_clip.end_sec
        duration = round(end - start, 2)

        if duration <= 0:
            raise ValueError(f"clip {semantic_clip.clip_id}: duration={duration}s <= 0, 跳过")

        kf_ts = semantic_clip.keyframe_timestamp_sec
        if kf_ts < start or kf_ts > end:
            kf_ts = round((start + end) / 2.0, 2)
            logger.warning(
                f"{semantic_clip.clip_id}: keyframe_timestamp {semantic_clip.keyframe_timestamp_sec} "
                f"out of [{start}, {end}], adjusted to {kf_ts}"
            )

        clip_path = clip_dir / "clip.mp4"
        keyframe_path = clip_dir / "keyframe.jpg"
        clip_json_path = clip_dir / "clip.json"

        # ── 切 clip ──
        cmd_clip = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(clip_path),
        ]
        logger.info(f"切 clip: {semantic_clip.clip_id} [{start}s - {end}s] -> {clip_path.name}")
        result = subprocess.run(cmd_clip, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 切 clip 失败 ({semantic_clip.clip_id}): {result.stderr[-500:]}")
        if not clip_path.exists():
            raise RuntimeError(f"ffmpeg 未生成 clip: {clip_path}")

        # ── 切 keyframe ──
        cmd_kf = [
            "ffmpeg", "-y",
            "-ss", str(kf_ts),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(keyframe_path),
        ]
        logger.info(f"切 keyframe: {semantic_clip.clip_id} @ {kf_ts}s -> {keyframe_path.name}")
        result = subprocess.run(cmd_kf, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 切 keyframe 失败 ({semantic_clip.clip_id}): {result.stderr[-500:]}")
        if not keyframe_path.exists():
            raise RuntimeError(f"ffmpeg 未生成 keyframe: {keyframe_path}")

        # ── 保存 clip.json ──
        clip_data = semantic_clip.model_dump()
        clip_data["clip_path"] = str(clip_path)
        clip_data["keyframe_path"] = str(keyframe_path)
        clip_json_path.write_text(
            json.dumps(clip_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "clip_path": str(clip_path),
            "keyframe_path": str(keyframe_path),
            "clip_json_path": str(clip_json_path),
        }

    @staticmethod
    def make_clip_dir_name(clip: SemanticClip) -> str:
        """生成 clip 文件夹名: {seq:02d}_{stage}_{visual_node}"""
        idx = f"{clip.sequence_index:02d}"
        stage = safe_filename(clip.primary_strategy_stage or "unknown")
        node = safe_filename(clip.visual_node_type or "unknown")
        return f"{idx}_{stage}_{node}"
