"""关键帧提取器 - ffmpeg 反切"""

import re
import subprocess
from pathlib import Path

from .logging_utils import setup_logger

logger = setup_logger(__name__)

STRATEGY_STAGE_SAFE = {
    "opening_hook": "opening_hook",
    "pain_point": "pain_point",
    "problem_amplification": "problem_amplification",
    "product_reveal": "product_reveal",
    "product_explanation": "product_explanation",
    "usage_demo": "usage_demo",
    "texture_demo": "texture_demo",
    "effect_proof": "effect_proof",
    "ingredient_proof": "ingredient_proof",
    "authority_endorsement": "authority_endorsement",
    "social_proof": "social_proof",
    "offer_price": "offer_price",
    "urgency_cta": "urgency_cta",
    "scene_transition": "scene_transition",
    "other": "other",
}


def _safe_filename(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


class KeyframeExtractor:
    def extract_keyframe(self, video_path: Path, keyframe: dict, output_dir: Path) -> dict:
        kf_id = keyframe["keyframe_id"]
        ts = max(0.0, float(keyframe.get("timestamp_sec", 0.0)))
        priority = int(keyframe.get("priority", 1))
        strategy_stage = STRATEGY_STAGE_SAFE.get(keyframe.get("strategy_stage", "other"), "other")
        frame_role = _safe_filename(keyframe.get("frame_role", "other"))

        fname = f"{priority:02d}_{kf_id}_{strategy_stage}_{frame_role}_{ts:.1f}.jpg"
        out_path = output_dir / fname

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(out_path),
        ]
        logger.info(f"ffmpeg 切帧: {kf_id} @ {ts}s -> {fname}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 失败: {result.stderr}")

        if not out_path.exists():
            raise RuntimeError(f"ffmpeg 未生成: {out_path}")

        return {
            "keyframe_id": kf_id,
            "timestamp_sec": ts,
            "priority": priority,
            "strategy_stage": strategy_stage,
            "frame_role": frame_role,
            "image_path": str(out_path),
            "aigc_reference_prompt": keyframe.get("aigc_reference_prompt", ""),
            "visual_description": keyframe.get("visual_description", ""),
        }
