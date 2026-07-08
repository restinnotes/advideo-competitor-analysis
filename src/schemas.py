"""Pydantic 数据模型 - 语义 clip 资产版"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ──────────────────── taxonomy tag ────────────────────


class TaxonomyTag(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    confidence: float = 0.0


# ──────────────────── video meta ────────────────────


class VideoMeta(BaseModel):
    estimated_duration_sec: float = 0.0
    language: str = "unknown"
    content_category: str = "unknown"
    has_visible_text: bool = False
    has_speech_or_voiceover: bool = False
    confidence: float = 0.0


# ──────────────────── video strategy ────────────────────


class VideoStrategy(BaseModel):
    generic_pattern_name: str = ""
    strategy_chain: list[str] = Field(default_factory=list)
    brand_free_pattern_summary: str = ""
    persuasion_logic: str = ""
    primary_conversion_driver: str = "unknown"
    hook_type_detail: TaxonomyTag = Field(default_factory=TaxonomyTag)
    proof_type_details: list[TaxonomyTag] = Field(default_factory=list)
    cta_type_detail: TaxonomyTag = Field(default_factory=TaxonomyTag)
    confidence: float = 0.0


# ──────────────────── visual elements ────────────────────


class FacePersonElement(BaseModel):
    has_person: bool = False
    face_visible: bool = False
    person_type: str = "unknown"
    person_count: int = 1
    action: str = ""
    expression_or_pose: str = ""
    confidence: float = 0.0


class ProductElement(BaseModel):
    has_product: bool = False
    category: str = ""
    brand_raw_visible_text: str = ""
    brand_normalized_guess: str = ""
    sku_or_product_raw_visible_text: str = ""
    packaging_description: str = ""
    usage_form: str = ""
    exposure_level: str = "none"
    confidence: float = 0.0


class PropElement(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    role_in_ad: str = "unknown"
    description: str = ""
    confidence: float = 0.0


class SceneStyleDetail(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    confidence: float = 0.0


class ProductionStyleDetail(BaseModel):
    raw_description: str = ""
    normalized_tag: str = "unknown"
    new_candidate: str = ""
    confidence: float = 0.0


class SceneElement(BaseModel):
    location_type: str = ""
    scene_style_detail: SceneStyleDetail = Field(default_factory=SceneStyleDetail)
    production_style_detail: ProductionStyleDetail = Field(default_factory=ProductionStyleDetail)
    background_description: str = ""
    lighting: str = ""
    color_palette: str = ""
    color_strategy: str = ""
    camera_style: str = ""
    composition: str = ""
    style_keywords: list[str] = Field(default_factory=list)


class ActionElement(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    action_type: str = ""
    body_part: str = ""
    object: str = ""
    description: str = ""
    role_in_strategy: str = ""
    confidence: float = 0.0


class VisibleTextElement(BaseModel):
    text: str = ""
    type: str = "other"
    role_in_strategy: str = ""
    confidence: float = 0.0


class SellingPointElement(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    evidence_source: str = "unknown"
    confidence: float = 0.0


class ConversionMethodElement(BaseModel):
    raw_description: str = ""
    normalized_tag: str = ""
    new_candidate: str = ""
    confidence: float = 0.0


class VisualElements(BaseModel):
    face_person: FacePersonElement = Field(default_factory=FacePersonElement)
    product: ProductElement = Field(default_factory=ProductElement)
    props: list[PropElement] = Field(default_factory=list)
    scene: SceneElement = Field(default_factory=SceneElement)
    actions: list[ActionElement] = Field(default_factory=list)
    visible_text: list[VisibleTextElement] = Field(default_factory=list)
    selling_points: list[SellingPointElement] = Field(default_factory=list)
    conversion_methods: list[ConversionMethodElement] = Field(default_factory=list)


# ──────────────────── clip keyframe ────────────────────


class ClipKeyframe(BaseModel):
    keyframe_id: str = ""
    timestamp_sec: float = 0.0
    visual_description: str = ""
    why_selected: str = ""
    aigc_reference_prompt: str = ""
    negative_prompt: str = ""


# ──────────────────── clip clustering features ────────────────────


class ClipClusteringFeatures(BaseModel):
    strategy_embedding_text: str = ""
    visual_embedding_text: str = ""
    entity_embedding_text: str = ""
    brand_free_clip_text: str = ""
    stage_code: str = ""
    visual_node_code: str = ""


# ──────────────────── clip quality flags ────────────────────


class ClipQualityFlags(BaseModel):
    fast_cut_risk: bool = False
    small_text_risk: bool = False
    product_identity_uncertain: bool = False
    celebrity_identity_uncertain: bool = False
    timestamp_precision_risk: bool = False
    strategy_stage_uncertain: bool = False
    clip_boundary_uncertain: bool = False
    needs_human_review: bool = False


# ──────────────────── semantic clip ────────────────────


class SemanticClip(BaseModel):
    clip_id: str = ""
    sequence_index: int = 1
    importance_rank: int = 1
    start_sec: float = 0.0
    end_sec: float = 0.0
    duration_sec: float = 0.0
    keyframe_timestamp_sec: float = 0.0
    approximate_time: bool = False
    primary_strategy_stage: str = "unknown"
    secondary_strategy_stages: list[str] = Field(default_factory=list)
    strategy_stage_detail: TaxonomyTag = Field(default_factory=TaxonomyTag)
    stage_position: str = "unknown"
    is_repeated_stage: bool = False
    stage_repeat_index: int = 1
    conversion_role: str = "unknown"
    clip_title: str = ""
    generic_strategy_label: str = ""
    visual_node_type: str = "unknown"
    visual_node_detail: TaxonomyTag = Field(default_factory=TaxonomyTag)
    what_happens_visually: str = ""
    what_is_said_or_shown_textually: str = ""
    persuasive_function: str = ""
    why_this_clip_exists: str = ""
    brand_free_strategy_description: str = ""
    evidence_dimensions: list[str] = Field(default_factory=list)
    visual_elements: VisualElements = Field(default_factory=VisualElements)
    keyframe: ClipKeyframe = Field(default_factory=ClipKeyframe)
    clustering_features: ClipClusteringFeatures = Field(default_factory=ClipClusteringFeatures)
    quality_flags: ClipQualityFlags = Field(default_factory=ClipQualityFlags)
    confidence: float = 0.0


# ──────────────────── video level tags ────────────────────


class VideoLevelTags(BaseModel):
    strategy_stages: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    selling_points: list[str] = Field(default_factory=list)
    creative_types: list[str] = Field(default_factory=list)
    visual_styles: list[str] = Field(default_factory=list)
    conversion_methods: list[str] = Field(default_factory=list)


# ──────────────────── video clustering features ────────────────────


class VideoClusteringFeatures(BaseModel):
    strategy_chain_code: str = ""
    generic_pattern_name: str = ""
    brand_free_strategy_embedding_text: str = ""
    visual_style_embedding_text: str = ""
    entity_embedding_text: str = ""
    tag_text: str = ""


# ──────────────────── video quality flags ────────────────────


class VideoQualityFlags(BaseModel):
    fast_cut_risk: bool = False
    small_text_risk: bool = False
    product_identity_uncertain: bool = False
    celebrity_identity_uncertain: bool = False
    timestamp_precision_risk: bool = False
    clip_boundary_uncertain: bool = False
    strategy_stage_uncertain: bool = False
    needs_human_review: bool = False


# ──────────────────── top-level result ────────────────────


class VideoAnalysisResult(BaseModel):
    taxonomy_version: str = "ad_taxonomy_v1"
    video_meta: VideoMeta = Field(default_factory=VideoMeta)
    video_strategy: VideoStrategy = Field(default_factory=VideoStrategy)
    semantic_clips: list[SemanticClip] = Field(default_factory=list)
    video_level_tags: VideoLevelTags = Field(default_factory=VideoLevelTags)
    video_clustering_features: VideoClusteringFeatures = Field(default_factory=VideoClusteringFeatures)
    quality_flags: VideoQualityFlags = Field(default_factory=VideoQualityFlags)


# ──────────────────── clip output (with paths) ────────────────────


class ClipOutput(BaseModel):
    clip_id: str = ""
    sequence_index: int = 1
    importance_rank: int = 1
    start_sec: float = 0.0
    end_sec: float = 0.0
    duration_sec: float = 0.0
    keyframe_timestamp_sec: float = 0.0
    primary_strategy_stage: str = ""
    secondary_strategy_stages: list[str] = Field(default_factory=list)
    strategy_stage_detail: dict[str, Any] = Field(default_factory=dict)
    stage_position: str = "unknown"
    is_repeated_stage: bool = False
    stage_repeat_index: int = 1
    conversion_role: str = "unknown"
    clip_title: str = ""
    generic_strategy_label: str = ""
    visual_node_type: str = ""
    visual_node_detail: dict[str, Any] = Field(default_factory=dict)
    what_happens_visually: str = ""
    persuasive_function: str = ""
    why_this_clip_exists: str = ""
    brand_free_strategy_description: str = ""
    visual_elements: dict[str, Any] = Field(default_factory=dict)
    keyframe: dict[str, Any] = Field(default_factory=dict)
    clustering_features: dict[str, Any] = Field(default_factory=dict)
    clip_path: str = ""
    keyframe_path: str = ""
    clip_json_path: str = ""
    quality_flags: dict[str, Any] = Field(default_factory=dict)


# ──────────────────── final result ────────────────────


class FinalResult(BaseModel):
    video_id: str
    model: str
    video_url: str = ""
    video_path: str = ""
    taxonomy_version: str = "ad_taxonomy_v1"
    video_meta: dict[str, Any] = Field(default_factory=dict)
    video_strategy: dict[str, Any] = Field(default_factory=dict)
    clip_outputs: list[dict[str, Any]] = Field(default_factory=list)
    video_level_tags: dict[str, Any] = Field(default_factory=dict)
    video_clustering_features: dict[str, Any] = Field(default_factory=dict)
    quality_flags: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ──────────────────── clip index ────────────────────


class ClipIndexEntry(BaseModel):
    clip_id: str = ""
    sequence_index: int = 1
    importance_rank: int = 1
    primary_strategy_stage: str = ""
    secondary_strategy_stages: list[str] = Field(default_factory=list)
    visual_node_type: str = ""
    start_sec: float = 0.0
    end_sec: float = 0.0
    duration_sec: float = 0.0
    keyframe_timestamp_sec: float = 0.0
    clip_path: str = ""
    keyframe_path: str = ""
    clip_json_path: str = ""
    clip_title: str = ""
    generic_strategy_label: str = ""
    brand_free_strategy_description: str = ""
    strategy_embedding_text: str = ""
    visual_embedding_text: str = ""
    entity_embedding_text: str = ""


class ClipIndex(BaseModel):
    video_id: str = ""
    model: str = ""
    clip_count: int = 0
    clips: list[ClipIndexEntry] = Field(default_factory=list)


# ──────────────────── normalization helpers ────────────────────

# Known stage position values
KNOWN_STAGE_POSITIONS = {"early", "middle", "late", "whole_video", "unknown"}
# Known conversion role values
KNOWN_CONVERSION_ROLES = {"attention", "resonance", "education", "proof", "desire", "offer", "action", "transition", "unknown"}
# Known person types
KNOWN_PERSON_TYPES = {"presenter", "model", "customer", "celebrity_or_kol", "hand_only", "none", "unknown"}
# Known exposure levels
KNOWN_EXPOSURE_LEVELS = {"none", "weak", "medium", "strong", "hero"}
# Known prop roles
KNOWN_PROP_ROLES = {"proof", "price", "usage", "display", "gift", "scene", "other", "unknown"}
# Known text types
KNOWN_TEXT_TYPES = {"subtitle", "brand", "product_name", "price", "selling_point", "cta", "ingredient", "proof", "watermark", "celebrity_tag", "other"}
# Known evidence sources
KNOWN_EVIDENCE_SOURCES = {"visual_text", "speech", "visual_object", "mixed", "unknown"}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def normalize_taxonomy_tag(raw: dict | TaxonomyTag | Any) -> TaxonomyTag:
    if isinstance(raw, TaxonomyTag):
        return raw
    if isinstance(raw, dict):
        return TaxonomyTag(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return TaxonomyTag(raw_description=str(raw) if raw else "")


def normalize_face_person(raw: dict | FacePersonElement | Any) -> FacePersonElement:
    if isinstance(raw, FacePersonElement):
        return raw
    if isinstance(raw, dict):
        pt = str(raw.get("person_type", "unknown"))
        if pt not in KNOWN_PERSON_TYPES:
            pt = "unknown"
        return FacePersonElement(
            has_person=bool(raw.get("has_person", False)),
            face_visible=bool(raw.get("face_visible", False)),
            person_type=pt,
            person_count=_safe_int(raw.get("person_count"), 1) or 1,
            action=str(raw.get("action", "")),
            expression_or_pose=str(raw.get("expression_or_pose", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return FacePersonElement()


def normalize_product(raw: dict | ProductElement | Any) -> ProductElement:
    if isinstance(raw, ProductElement):
        return raw
    if isinstance(raw, dict):
        el = str(raw.get("exposure_level", "none"))
        if el not in KNOWN_EXPOSURE_LEVELS:
            el = "none"
        return ProductElement(
            has_product=bool(raw.get("has_product", False)),
            category=str(raw.get("category", "")),
            brand_raw_visible_text=str(raw.get("brand_raw_visible_text", "")),
            brand_normalized_guess=str(raw.get("brand_normalized_guess", "")),
            sku_or_product_raw_visible_text=str(raw.get("sku_or_product_raw_visible_text", "")),
            packaging_description=str(raw.get("packaging_description", "")),
            usage_form=str(raw.get("usage_form", "")),
            exposure_level=el,
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return ProductElement()


def normalize_prop(raw: dict | PropElement | Any) -> PropElement:
    if isinstance(raw, PropElement):
        return raw
    if isinstance(raw, dict):
        role = str(raw.get("role_in_ad", "unknown"))
        if role not in KNOWN_PROP_ROLES:
            role = "unknown"
        return PropElement(
            raw_description=str(raw.get("raw_description", raw.get("name", ""))),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            role_in_ad=role,
            description=str(raw.get("description", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    if isinstance(raw, str):
        return PropElement(raw_description=raw, description=raw)
    return PropElement()


def _make_scene_style_detail(raw: Any) -> SceneStyleDetail:
    if isinstance(raw, SceneStyleDetail):
        return raw
    if isinstance(raw, dict):
        return SceneStyleDetail(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return SceneStyleDetail()


def _make_production_style_detail(raw: Any) -> ProductionStyleDetail:
    if isinstance(raw, ProductionStyleDetail):
        return raw
    if isinstance(raw, dict):
        return ProductionStyleDetail(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "unknown")),
            new_candidate=str(raw.get("new_candidate", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return ProductionStyleDetail()


def normalize_scene(raw: dict | SceneElement | Any) -> SceneElement:
    if isinstance(raw, SceneElement):
        return raw
    if isinstance(raw, dict):
        cp = raw.get("color_palette", "")
        if isinstance(cp, list):
            cp = ", ".join(str(x) for x in cp)
        return SceneElement(
            location_type=str(raw.get("location_type", "")),
            scene_style_detail=_make_scene_style_detail(raw.get("scene_style_detail", {})),
            production_style_detail=_make_production_style_detail(raw.get("production_style_detail", {})),
            background_description=str(raw.get("background_description", "")),
            lighting=str(raw.get("lighting", "")),
            color_palette=str(cp),
            color_strategy=str(raw.get("color_strategy", "")),
            camera_style=str(raw.get("camera_style", "")),
            composition=str(raw.get("composition", "")),
            style_keywords=raw.get("style_keywords", []) if isinstance(raw.get("style_keywords"), list) else [],
        )
    return SceneElement()


def normalize_action(raw: dict | ActionElement | Any) -> ActionElement:
    if isinstance(raw, ActionElement):
        return raw
    if isinstance(raw, dict):
        return ActionElement(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            action_type=str(raw.get("action_type", "")),
            body_part=str(raw.get("body_part", "")),
            object=str(raw.get("object", "")),
            description=str(raw.get("description", "")),
            role_in_strategy=str(raw.get("role_in_strategy", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return ActionElement()


def normalize_visible_text(raw: dict | VisibleTextElement | Any) -> VisibleTextElement:
    if isinstance(raw, VisibleTextElement):
        return raw
    if isinstance(raw, dict):
        return VisibleTextElement(
            text=str(raw.get("text", "")),
            type=str(raw.get("type", "other")),
            role_in_strategy=str(raw.get("role_in_strategy", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    if isinstance(raw, str):
        return VisibleTextElement(text=raw)
    return VisibleTextElement()


def normalize_selling_point(raw: dict | SellingPointElement | Any) -> SellingPointElement:
    if isinstance(raw, SellingPointElement):
        return raw
    if isinstance(raw, dict):
        return SellingPointElement(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            evidence_source=str(raw.get("evidence_source", "unknown")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return SellingPointElement()


def normalize_conversion_method(raw: dict | ConversionMethodElement | Any) -> ConversionMethodElement:
    if isinstance(raw, ConversionMethodElement):
        return raw
    if isinstance(raw, dict):
        return ConversionMethodElement(
            raw_description=str(raw.get("raw_description", "")),
            normalized_tag=str(raw.get("normalized_tag", "")),
            new_candidate=str(raw.get("new_candidate", "")),
            confidence=_safe_float(raw.get("confidence"), 0.0),
        )
    return ConversionMethodElement()


def normalize_visual_elements(raw: dict | VisualElements | Any) -> VisualElements:
    if isinstance(raw, VisualElements):
        return raw
    if not isinstance(raw, dict):
        return VisualElements()

    ve = raw
    face_person = normalize_face_person(ve.get("face_person", {}))
    product = normalize_product(ve.get("product", {}))
    props = [normalize_prop(p) for p in ve.get("props", []) if p]
    scene = normalize_scene(ve.get("scene", {}))
    actions = [normalize_action(a) for a in ve.get("actions", []) if a]
    visible_text = [normalize_visible_text(vt) for vt in ve.get("visible_text", []) if vt]
    selling_points = [normalize_selling_point(sp) for sp in ve.get("selling_points", []) if sp]
    conversion_methods = [normalize_conversion_method(cm) for cm in ve.get("conversion_methods", []) if cm]

    return VisualElements(
        face_person=face_person,
        product=product,
        props=props,
        scene=scene,
        actions=actions,
        visible_text=visible_text,
        selling_points=selling_points,
        conversion_methods=conversion_methods,
    )


def normalize_clip(raw: dict | SemanticClip | Any, idx: int = 0) -> SemanticClip:
    """Normalize a single semantic clip dict into SemanticClip, fixing common issues."""
    if isinstance(raw, SemanticClip):
        return raw
    if not isinstance(raw, dict):
        return SemanticClip(sequence_index=idx + 1)

    clip = SemanticClip()

    # Basic fields
    clip.clip_id = str(raw.get("clip_id", f"clip_{idx + 1:03d}"))
    clip.sequence_index = _safe_int(raw.get("sequence_index"), idx + 1)
    clip.importance_rank = _safe_int(raw.get("importance_rank"), idx + 1)
    clip.start_sec = _safe_float(raw.get("start_sec"), 0.0)
    clip.end_sec = _safe_float(raw.get("end_sec"), 0.0)
    clip.keyframe_timestamp_sec = _safe_float(raw.get("keyframe_timestamp_sec"), 0.0)
    clip.approximate_time = bool(raw.get("approximate_time", False))

    # Fix end_sec <= start_sec
    warnings: list[str] = []
    if clip.end_sec <= clip.start_sec:
        clip.end_sec = clip.start_sec + 1.0
        warnings.append(f"end_sec <= start_sec, adjusted to {clip.end_sec}")

    # Fix keyframe_timestamp_sec
    if clip.keyframe_timestamp_sec < clip.start_sec or clip.keyframe_timestamp_sec > clip.end_sec:
        clip.keyframe_timestamp_sec = (clip.start_sec + clip.end_sec) / 2.0
        warnings.append(f"keyframe_timestamp_sec out of range, adjusted to {clip.keyframe_timestamp_sec}")

    # duration
    clip.duration_sec = round(clip.end_sec - clip.start_sec, 2)

    # Strategy fields
    clip.primary_strategy_stage = str(raw.get("primary_strategy_stage", "unknown"))
    clip.secondary_strategy_stages = raw.get("secondary_strategy_stages", []) if isinstance(raw.get("secondary_strategy_stages"), list) else []
    clip.strategy_stage_detail = normalize_taxonomy_tag(raw.get("strategy_stage_detail", {}))

    stage_pos = str(raw.get("stage_position", "unknown"))
    clip.stage_position = stage_pos if stage_pos in KNOWN_STAGE_POSITIONS else "unknown"
    clip.is_repeated_stage = bool(raw.get("is_repeated_stage", False))
    clip.stage_repeat_index = _safe_int(raw.get("stage_repeat_index"), 1) or 1

    conv_role = str(raw.get("conversion_role", "unknown"))
    clip.conversion_role = conv_role if conv_role in KNOWN_CONVERSION_ROLES else "unknown"

    clip.clip_title = str(raw.get("clip_title", ""))
    clip.generic_strategy_label = str(raw.get("generic_strategy_label", ""))
    clip.visual_node_type = str(raw.get("visual_node_type", "unknown"))
    clip.visual_node_detail = normalize_taxonomy_tag(raw.get("visual_node_detail", {}))

    clip.what_happens_visually = str(raw.get("what_happens_visually", ""))
    clip.what_is_said_or_shown_textually = str(raw.get("what_is_said_or_shown_textually", ""))
    clip.persuasive_function = str(raw.get("persuasive_function", ""))
    clip.why_this_clip_exists = str(raw.get("why_this_clip_exists", ""))
    clip.brand_free_strategy_description = str(raw.get("brand_free_strategy_description", ""))

    clip.evidence_dimensions = raw.get("evidence_dimensions", []) if isinstance(raw.get("evidence_dimensions"), list) else []

    # Visual elements
    clip.visual_elements = normalize_visual_elements(raw.get("visual_elements", {}))

    # Keyframe
    kf_raw = raw.get("keyframe", {})
    if isinstance(kf_raw, dict):
        clip.keyframe = ClipKeyframe(
            keyframe_id=str(kf_raw.get("keyframe_id", "")),
            timestamp_sec=_safe_float(kf_raw.get("timestamp_sec"), clip.keyframe_timestamp_sec),
            visual_description=str(kf_raw.get("visual_description", "")),
            why_selected=str(kf_raw.get("why_selected", "")),
            aigc_reference_prompt=str(kf_raw.get("aigc_reference_prompt", "")),
            negative_prompt=str(kf_raw.get("negative_prompt", "")),
        )
    else:
        clip.keyframe = ClipKeyframe(timestamp_sec=clip.keyframe_timestamp_sec)

    # Clustering features
    cf_raw = raw.get("clustering_features", {})
    if isinstance(cf_raw, dict):
        clip.clustering_features = ClipClusteringFeatures(
            strategy_embedding_text=str(cf_raw.get("strategy_embedding_text", "")),
            visual_embedding_text=str(cf_raw.get("visual_embedding_text", "")),
            entity_embedding_text=str(cf_raw.get("entity_embedding_text", "")),
            brand_free_clip_text=str(cf_raw.get("brand_free_clip_text", "")),
            stage_code=str(cf_raw.get("stage_code", "")),
            visual_node_code=str(cf_raw.get("visual_node_code", "")),
        )

    # Quality flags
    qf_raw = raw.get("quality_flags", {})
    if isinstance(qf_raw, dict):
        clip.quality_flags = ClipQualityFlags(
            fast_cut_risk=bool(qf_raw.get("fast_cut_risk", False)),
            small_text_risk=bool(qf_raw.get("small_text_risk", False)),
            product_identity_uncertain=bool(qf_raw.get("product_identity_uncertain", False)),
            celebrity_identity_uncertain=bool(qf_raw.get("celebrity_identity_uncertain", False)),
            timestamp_precision_risk=bool(qf_raw.get("timestamp_precision_risk", False)),
            strategy_stage_uncertain=bool(qf_raw.get("strategy_stage_uncertain", False)),
            clip_boundary_uncertain=bool(qf_raw.get("clip_boundary_uncertain", False)),
            needs_human_review=bool(qf_raw.get("needs_human_review", False)),
        )

    clip.confidence = _safe_float(raw.get("confidence"), 0.0)

    return clip


def normalize_result(raw: dict) -> VideoAnalysisResult:
    """Normalize raw model output into VideoAnalysisResult."""
    result = VideoAnalysisResult()

    # taxonomy_version
    result.taxonomy_version = str(raw.get("taxonomy_version", "ad_taxonomy_v1"))

    # video_meta
    vm_raw = raw.get("video_meta", {})
    if isinstance(vm_raw, dict):
        result.video_meta = VideoMeta(
            estimated_duration_sec=_safe_float(vm_raw.get("estimated_duration_sec")),
            language=str(vm_raw.get("language", "unknown")),
            content_category=str(vm_raw.get("content_category", "unknown")),
            has_visible_text=bool(vm_raw.get("has_visible_text", False)),
            has_speech_or_voiceover=bool(vm_raw.get("has_speech_or_voiceover", False)),
            confidence=_safe_float(vm_raw.get("confidence")),
        )

    # video_strategy (handle both old strategy_pattern and new video_strategy)
    vs_raw = raw.get("video_strategy") or raw.get("strategy_pattern") or {}
    if isinstance(vs_raw, dict):
        result.video_strategy = VideoStrategy(
            generic_pattern_name=str(vs_raw.get("generic_pattern_name", vs_raw.get("pattern_name", ""))),
            strategy_chain=vs_raw.get("strategy_chain", []) if isinstance(vs_raw.get("strategy_chain"), list) else [],
            brand_free_pattern_summary=str(vs_raw.get("brand_free_pattern_summary", vs_raw.get("pattern_summary", ""))),
            persuasion_logic=str(vs_raw.get("persuasion_logic", "")),
            primary_conversion_driver=str(vs_raw.get("primary_conversion_driver", "unknown")),
            hook_type_detail=normalize_taxonomy_tag(vs_raw.get("hook_type_detail", {})),
            proof_type_details=[normalize_taxonomy_tag(p) for p in vs_raw.get("proof_type_details", []) if p],
            cta_type_detail=normalize_taxonomy_tag(vs_raw.get("cta_type_detail", {})),
            confidence=_safe_float(vs_raw.get("confidence")),
        )

    # semantic_clips (handle both new and old formats)
    clips_raw = raw.get("semantic_clips", [])
    if not clips_raw and raw.get("strategy_timeline"):
        # Old format: convert strategy_timeline + keyframes to semantic_clips
        clips_raw = _convert_old_timeline_to_clips(raw)

    if isinstance(clips_raw, list):
        normalized_clips = []
        for i, c in enumerate(clips_raw):
            nc = normalize_clip(c, i)
            normalized_clips.append(nc)

        # Fix sequence_index if missing or duplicated
        _fix_sequence_indices(normalized_clips)
        # Fix importance_rank if duplicated
        _fix_importance_ranks(normalized_clips)
        # Sort by sequence_index
        normalized_clips.sort(key=lambda x: x.sequence_index)
        result.semantic_clips = normalized_clips

    # video_level_tags
    vlt_raw = raw.get("video_level_tags") or raw.get("tags") or {}
    if isinstance(vlt_raw, dict):
        result.video_level_tags = VideoLevelTags(
            strategy_stages=vlt_raw.get("strategy_stages", []) if isinstance(vlt_raw.get("strategy_stages"), list) else [],
            people=vlt_raw.get("people", []) if isinstance(vlt_raw.get("people"), list) else [],
            products=vlt_raw.get("products", []) if isinstance(vlt_raw.get("products"), list) else [],
            props=vlt_raw.get("props", []) if isinstance(vlt_raw.get("props"), list) else [],
            scenes=vlt_raw.get("scenes", []) if isinstance(vlt_raw.get("scenes"), list) else [],
            actions=vlt_raw.get("actions", []) if isinstance(vlt_raw.get("actions"), list) else [],
            selling_points=vlt_raw.get("selling_points", []) if isinstance(vlt_raw.get("selling_points"), list) else [],
            creative_types=vlt_raw.get("creative_types", []) if isinstance(vlt_raw.get("creative_types"), list) else [],
            visual_styles=vlt_raw.get("visual_styles", []) if isinstance(vlt_raw.get("visual_styles"), list) else [],
            conversion_methods=vlt_raw.get("conversion_methods", []) if isinstance(vlt_raw.get("conversion_methods"), list) else [],
        )

    # video_clustering_features
    vcf_raw = raw.get("video_clustering_features") or raw.get("pattern_for_clustering") or {}
    if isinstance(vcf_raw, dict):
        result.video_clustering_features = VideoClusteringFeatures(
            strategy_chain_code=str(vcf_raw.get("strategy_chain_code", vcf_raw.get("stage_sequence_text", ""))),
            generic_pattern_name=str(vcf_raw.get("generic_pattern_name", vcf_raw.get("short_pattern_text", ""))),
            brand_free_strategy_embedding_text=str(vcf_raw.get("brand_free_strategy_embedding_text", vcf_raw.get("long_pattern_text", ""))),
            visual_style_embedding_text=str(vcf_raw.get("visual_style_embedding_text", vcf_raw.get("key_visual_sequence_text", ""))),
            entity_embedding_text=str(vcf_raw.get("entity_embedding_text", "")),
            tag_text=str(vcf_raw.get("tag_text", "")),
        )

    # quality_flags
    qf_raw = raw.get("quality_flags", {})
    if isinstance(qf_raw, dict):
        result.quality_flags = VideoQualityFlags(
            fast_cut_risk=bool(qf_raw.get("fast_cut_risk", False)),
            small_text_risk=bool(qf_raw.get("small_text_risk", False)),
            product_identity_uncertain=bool(qf_raw.get("product_identity_uncertain", False)),
            celebrity_identity_uncertain=bool(qf_raw.get("celebrity_identity_uncertain", False)),
            timestamp_precision_risk=bool(qf_raw.get("timestamp_precision_risk", False)),
            clip_boundary_uncertain=bool(qf_raw.get("clip_boundary_uncertain", False)),
            strategy_stage_uncertain=bool(qf_raw.get("strategy_stage_uncertain", False)),
            needs_human_review=bool(qf_raw.get("needs_human_review", False)),
        )

    return result


def _fix_sequence_indices(clips: list[SemanticClip]) -> None:
    """Ensure sequence_index is sequential from 1."""
    seen = set()
    has_dup = False
    has_zero = False
    for c in clips:
        if c.sequence_index in seen or c.sequence_index <= 0:
            has_dup = True
            break
        seen.add(c.sequence_index)

    if has_dup:
        for i, c in enumerate(clips):
            c.sequence_index = i + 1


def _fix_importance_ranks(clips: list[SemanticClip]) -> None:
    """Ensure importance_rank is unique."""
    seen = set()
    has_dup = False
    for c in clips:
        if c.importance_rank in seen:
            has_dup = True
            break
        seen.add(c.importance_rank)

    if has_dup:
        # Sort by start_sec, then assign ranks
        sorted_clips = sorted(clips, key=lambda x: (x.start_sec, x.sequence_index))
        for i, c in enumerate(sorted_clips):
            c.importance_rank = i + 1


def _convert_old_timeline_to_clips(raw: dict) -> list[dict]:
    """Convert old strategy_timeline + keyframes format to semantic_clips."""
    timeline = raw.get("strategy_timeline", [])
    keyframes = raw.get("keyframes", [])

    # Index keyframes by source_segment_id
    kf_by_seg: dict[int, list[dict]] = {}
    for kf in keyframes:
        if not isinstance(kf, dict):
            continue
        sid = int(kf.get("source_segment_id", 0))
        kf_by_seg.setdefault(sid, []).append(kf)

    clips = []
    for i, seg in enumerate(timeline):
        if not isinstance(seg, dict):
            continue

        seg_id = int(seg.get("segment_id", i + 1))
        seg_kfs = kf_by_seg.get(seg_id, [])
        # Pick best keyframe (highest priority / first)
        best_kf = seg_kfs[0] if seg_kfs else {}

        clip: dict[str, Any] = {
            "clip_id": f"clip_{i + 1:03d}",
            "sequence_index": i + 1,
            "importance_rank": i + 1,
            "start_sec": _safe_float(seg.get("start_sec")),
            "end_sec": _safe_float(seg.get("end_sec")),
            "keyframe_timestamp_sec": _safe_float(best_kf.get("timestamp_sec", seg.get("suggested_keyframe_timestamp_sec", 0.0))),
            "approximate_time": bool(best_kf.get("approximate_timestamp", False)),
            "primary_strategy_stage": str(seg.get("strategy_stage", "unknown")),
            "secondary_strategy_stages": [],
            "clip_title": str(seg.get("segment_title", "")),
            "what_happens_visually": str(seg.get("what_happens_visually", "")),
            "what_is_said_or_shown_textually": str(seg.get("what_is_said_or_shown_textually", "")),
            "persuasive_function": str(seg.get("persuasive_function", "")),
            "why_this_clip_exists": str(seg.get("why_this_segment_exists", "")),
            "evidence_dimensions": seg.get("evidence_dimensions", []) if isinstance(seg.get("evidence_dimensions"), list) else [],
            "confidence": _safe_float(seg.get("confidence")),
        }

        # Build visual_elements from old important_visual_elements
        ive = seg.get("important_visual_elements", {})
        if isinstance(ive, dict):
            clip["visual_elements"] = {
                "face_person": {"action": str(ive.get("face_person", ""))},
                "product": {"category": str(ive.get("product", ""))},
                "props": [{"description": str(ive.get("prop", ""))}],
                "scene": {"location_type": str(ive.get("scene", ""))},
            }

        # Map keyframe fields
        if best_kf:
            clip["keyframe"] = {
                "keyframe_id": best_kf.get("keyframe_id", ""),
                "timestamp_sec": clip["keyframe_timestamp_sec"],
                "visual_description": best_kf.get("visual_description", ""),
                "why_selected": best_kf.get("why_selected", ""),
                "aigc_reference_prompt": best_kf.get("aigc_reference_prompt", ""),
                "negative_prompt": best_kf.get("negative_prompt", ""),
            }

        clips.append(clip)

    return clips
