"""Portable, offline Higgsfield production-package export."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

from .artifacts import *
from .core import *


def portable_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def higgsfield_handle(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return f"@{token or 'reference'}"


def higgsfield_reference_category(asset_type: str) -> str:
    return HIGGSFIELD_REFERENCE_CATEGORIES.get(asset_type, "other")


def _run_self_validation(project_dir: Path) -> dict[str, Any]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        returncode = validate_project(project_dir, True)
    try:
        payload = json.loads(stdout.getvalue())
    except json.JSONDecodeError as exc:
        raise RuntimeError(stderr.getvalue().strip() or stdout.getvalue().strip() or str(exc)) from exc
    payload["returncode"] = returncode
    return payload


def _shot_reference_bindings(
    shot: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    spatial_map: dict[str, Any],
    character_states: dict[str, dict[str, Any]],
    location_states: dict[str, dict[str, Any]],
    prop_states: dict[str, dict[str, Any]],
    handles: dict[str, str],
    portable_paths: dict[str, str],
) -> list[dict[str, Any]]:
    seeds: list[tuple[str, str, bool]] = []
    start_id = shot.get("start_keyframe_id")
    character_bindings = shot.get("character_state_bindings") if isinstance(shot.get("character_state_bindings"), dict) else {}
    for root_asset_id in shot.get("cast_asset_ids", []):
        if not isinstance(root_asset_id, str) or not root_asset_id:
            continue
        state_id = character_bindings.get(root_asset_id)
        state_asset_id = character_states.get(state_id, {}).get("authority_asset_id")
        state_asset = assets.get(state_asset_id, {})
        roots = state_asset.get("root_reference_ids") if isinstance(state_asset.get("root_reference_ids"), list) else [root_asset_id]
        root_usage = {
            "character_identity_inspector": "identity_inspector_primary",
            "character_face_anchor": "root_identity_face",
            "character_body_anchor": "root_identity_body",
            "character_identity_view": "root_identity_angle",
            "character_master": "root_identity_turnaround",
        }
        for identity_root_id in roots:
            if isinstance(identity_root_id, str) and identity_root_id:
                seeds.append((identity_root_id, root_usage.get(str(assets.get(identity_root_id, {}).get("type")), "root_identity"), True))
        if isinstance(state_asset_id, str) and state_asset_id:
            seeds.append((state_asset_id, "current_character_state", True))
    for pose_anchor_id in shot.get("pose_contact_anchor_ids", []):
        if isinstance(pose_anchor_id, str) and pose_anchor_id:
            seeds.append((pose_anchor_id, "pose_contact_anchor", True))
    location_id = shot.get("location_asset_id")
    if isinstance(location_id, str) and location_id:
        seeds.append((location_id, "location_shot_view", True))
    three_quarter_id = spatial_map.get("side_three_quarter_view_asset_id")
    if isinstance(three_quarter_id, str) and three_quarter_id:
        seeds.append((three_quarter_id, "location_three_quarter", True))
    location_state = location_states.get(shot.get("location_state_id"), {})
    for asset_id in location_state.get("authority_asset_ids", []):
        if isinstance(asset_id, str) and asset_id not in {location_id, three_quarter_id}:
            seeds.append((asset_id, "location_state_view", True))
    primary_anchor = spatial_map.get("primary_anchor") if isinstance(spatial_map.get("primary_anchor"), dict) else {}
    anchor_id = primary_anchor.get("asset_id")
    if isinstance(anchor_id, str) and anchor_id:
        seeds.append((anchor_id, "spatial_anchor", True))
    for asset_id in shot.get("prop_asset_ids", []):
        if isinstance(asset_id, str) and asset_id:
            seeds.append((asset_id, "spatial_anchor" if asset_id == anchor_id else "root_prop", True))
            state_id = (shot.get("prop_state_bindings") or {}).get(asset_id) if isinstance(shot.get("prop_state_bindings"), dict) else None
            state_asset_id = prop_states.get(state_id, {}).get("authority_asset_id")
            if isinstance(state_asset_id, str) and state_asset_id:
                seeds.append((state_asset_id, "current_prop_state", True))
    profile = profiles.get(shot.get("capture_profile_id"), {})
    look_id = profile.get("approved_look_test_id")
    if isinstance(look_id, str) and look_id:
        seeds.append((look_id, "approved_look", False))
    sequence_anchor_id = shot.get("sequence_visual_anchor_asset_id")
    if isinstance(sequence_anchor_id, str) and sequence_anchor_id:
        seeds.append((sequence_anchor_id, "sequence_visual_anchor", True))
    if isinstance(start_id, str) and start_id:
        seeds.append((start_id, "start_frame", True))
    end_id = shot.get("end_keyframe_id")
    if isinstance(end_id, str) and end_id:
        seeds.append((end_id, "end_frame", True))

    bindings: list[dict[str, Any]] = []
    seen: set[str] = set()
    explicit_ids = {asset_id for asset_id, _, _ in seeds}
    for asset_id, usage, required in seeds:
        if asset_id in seen:
            continue
        asset = assets.get(asset_id)
        if not asset or asset.get("status") != "approved" or asset_id not in portable_paths:
            continue
        seen.add(asset_id)
        bindings.append(
            {
                "rank": len(bindings) + 1,
                "asset_id": asset_id,
                "asset_type": asset.get("type"),
                "usage": usage,
                "required": required,
                "suggested_handle": handles[asset_id],
                "file": portable_paths[asset_id],
            }
        )
    for asset_id, _, _ in seeds:
        for dependency_id in _asset_dependency_ids(asset_id, assets):
            if dependency_id in seen or dependency_id in explicit_ids:
                continue
            asset = assets.get(dependency_id)
            if not asset or asset.get("status") != "approved" or dependency_id not in portable_paths:
                continue
            seen.add(dependency_id)
            bindings.append(
                {
                    "rank": len(bindings) + 1,
                    "asset_id": dependency_id,
                    "asset_type": asset.get("type"),
                    "usage": "source_anchor",
                    "required": False,
                    "suggested_handle": handles[dependency_id],
                    "file": portable_paths[dependency_id],
                }
            )
    return bindings


def _higgsfield_prompt(source_prompt: str, bindings: list[dict[str, Any]]) -> str:
    portable_prompt = source_prompt
    for binding in sorted(bindings, key=lambda item: len(str(item["asset_id"])), reverse=True):
        portable_prompt = portable_prompt.replace(str(binding["asset_id"]), str(binding["suggested_handle"]))
    # prompt.txt must be directly pasteable.  Upload instructions and reference
    # responsibilities live in references.csv/reference-map.json, not in the
    # model-facing prompt, whose first line must be GLOBAL STYLE.
    return portable_prompt.strip() + "\n"


def _official_prompt_sections(text: str) -> dict[str, str]:
    """Parse one compiler-owned Seedance 2.5 prompt without accepting prose aliases."""
    headings = {value.upper(): value for value in VIDEO_PROMPT_HEADERS}
    sections: dict[str, list[str]] = {}
    current = ""
    for raw_line in text.splitlines():
        normalized = raw_line.strip().rstrip(":").upper()
        if normalized in headings:
            current = headings[normalized]
            sections[current] = []
        elif current:
            sections[current].append(raw_line.strip())
        elif raw_line.strip():
            raise ValueError("official Higgsfield prompt contains text before GLOBAL STYLE")
    missing = [heading for heading in VIDEO_PROMPT_HEADERS if heading not in sections]
    if missing:
        raise ValueError(f"official Higgsfield prompt is missing sections: {missing}")
    return {heading: " ".join(line for line in lines if line).strip() for heading, lines in sections.items()}


def _merge_official_sequence_prompt(source_prompts: list[str]) -> str:
    """Merge single-shot compiler output into Higgsfield's official multi-shot shape."""
    if not source_prompts:
        raise ValueError("cannot build a sequence prompt without shots")
    parsed = [_official_prompt_sections(text) for text in source_prompts]
    def block(heading: str, body: str) -> str:
        compact = re.sub(r"\s+", " ", body).strip()
        return f"{heading}\n{compact}\n"

    blocks: list[str] = []
    blocks.append(block("GLOBAL STYLE", parsed[0]["GLOBAL STYLE"] + " The same approved references, identity, wardrobe, location state, lighting logic and surface behavior hold through every cut."))
    blocks.append(block("SCENE", "Sequence: " + " ".join(section["SCENE"] for section in parsed)))
    blocks.append(block("CHARACTERS", parsed[0]["CHARACTERS"] + " Preserve these exact characters across all numbered shots."))
    blocks.append(block("LOCATION", parsed[0]["LOCATION"] + " The physical geography and set-fixed axes do not reset after a cut."))
    blocks.append(block("FIRST FRAME AND BLOCKING", parsed[0]["FIRST FRAME AND BLOCKING"]))
    for index, section in enumerate(parsed, start=1):
        ending = " Hard cut." if index < len(parsed) else " End sequence."
        blocks.append(block(f"Shot {index}", section["Shot 1"] + ending))
    blocks.append(block("OPTICS", " ".join(f"Shot {index}: {section['OPTICS']}" for index, section in enumerate(parsed, start=1))))
    blocks.append(block("CAMERA", " ".join(f"Shot {index}: {section['CAMERA']}" for index, section in enumerate(parsed, start=1))))
    blocks.append(block("PHYSICS", " ".join(f"Shot {index}: {section['PHYSICS']}" for index, section in enumerate(parsed, start=1))))
    blocks.append(block("LIGHTING", " ".join(f"Shot {index}: {section['LIGHTING']}" for index, section in enumerate(parsed, start=1))))
    blocks.append(block("AUDIO", " ".join(f"Shot {index}: {section['AUDIO']}" for index, section in enumerate(parsed, start=1))))
    return "\n".join(blocks).strip() + "\n"


def _resolved_shot_spatial_payload(
    shot: dict[str, Any],
    spatial_map: dict[str, Any],
    handles: dict[str, str],
) -> dict[str, Any]:
    marks = _spatial_mark_index(spatial_map)
    camera_mark_id = str(shot.get("camera_mark_id", ""))
    subject_mark_ids = shot.get("subject_mark_ids") if isinstance(shot.get("subject_mark_ids"), dict) else {}
    anchor = dict(spatial_map.get("primary_anchor", {})) if isinstance(spatial_map.get("primary_anchor"), dict) else {}
    anchor_id = str(anchor.get("asset_id", ""))
    anchor["suggested_handle"] = handles.get(anchor_id, higgsfield_handle(anchor_id))
    subject_marks = []
    for asset_id in sorted(subject_mark_ids):
        mark_id = str(subject_mark_ids[asset_id])
        subject_marks.append(
            {
                "asset_id": asset_id,
                "suggested_handle": handles.get(asset_id, higgsfield_handle(asset_id)),
                "mark": marks.get(mark_id, {}),
            }
        )
    cast_ids = set(shot.get("cast_asset_ids", [])) if isinstance(shot.get("cast_asset_ids"), list) else set()
    movement_paths = [
        movement
        for movement in spatial_map.get("movement_paths", [])
        if isinstance(movement, dict) and movement.get("subject_asset_id") in cast_ids
    ]
    return {
        "package_schema": f"higgsfield-spatial-map-{HIGGSFIELD_PACKAGE_VERSION}",
        "spatial_map_id": spatial_map.get("id"),
        "scene_id": spatial_map.get("scene_id"),
        "scene_state_id": spatial_map.get("scene_state_id"),
        "location_master_asset_id": spatial_map.get("location_master_asset_id"),
        "establishing_view_asset_id": spatial_map.get("establishing_view_asset_id"),
        "side_three_quarter_view_asset_id": spatial_map.get("side_three_quarter_view_asset_id"),
        "primary_anchor": anchor,
        "coordinate_system": spatial_map.get("coordinate_system"),
        "landmarks": spatial_map.get("landmarks", []),
        "camera_mark": marks.get(camera_mark_id, {}),
        "subject_marks": subject_marks,
        "movement_paths": movement_paths,
        "anchor_projection": shot.get("anchor_projection"),
        "multi_person_projection": shot.get("multi_person_projection"),
        "dramatic_coverage_plan": shot.get("dramatic_coverage_plan"),
        "subject_environment_integration": shot.get("subject_environment_integration"),
        "depth_order": shot.get("depth_order"),
        "deterministic_prompt_block": render_spatial_prompt_block(shot, spatial_map),
    }


def _higgsfield_settings(
    project: dict[str, Any],
    shot: dict[str, Any],
    bindings: list[dict[str, Any]],
    prompt_file: str,
    spatial_file: str,
    spatial_payload: dict[str, Any],
    format_file: str,
    camera_path_file: str,
    environment_file: str,
    temporal_file: str,
    dynamic_range_file: str,
    commercial_direction_file: str = "",
) -> dict[str, Any]:
    adapter_notes = shot.get("adapter_notes") if isinstance(shot.get("adapter_notes"), dict) else {}
    overrides = adapter_notes.get("higgsfield") if isinstance(adapter_notes.get("higgsfield"), dict) else {}
    audio = shot.get("audio") if isinstance(shot.get("audio"), dict) else {}
    has_audio_direction = any(bool(audio.get(key)) for key in ("dialogue", "ambience", "foley", "music", "silence"))
    start_frame = next((item for item in bindings if item["usage"] == "start_frame"), None)
    end_frame = next((item for item in bindings if item["usage"] == "end_frame"), None)

    provider_fields = {
        "surface": str(overrides.get("surface") or "Cinema Studio 4"),
        "model": "Seedance 2.5",
        "official_conformance_profile_id": HIGGSFIELD_OFFICIAL_PROFILE_ID,
        "knowledge_snapshot": HIGGSFIELD_KNOWLEDGE_SNAPSHOT,
        "model_version_policy": "snapshot-must-match-or-block",
        "input_mode": str(
            overrides.get("input_mode")
            or ("start/end-frame-with-references" if end_frame else "start-frame-with-references" if start_frame else "multi-reference")
        ),
        "genre": str(overrides.get("genre") or "General"),
        "speed_ramp": str(overrides.get("speed_ramp") or "Linear"),
        "tempo": str(overrides.get("tempo") or "Single Shot"),
        "resolution": str(overrides.get("resolution") or "1080p-if-current-model-supports-it"),
        "audio_mode": str(overrides.get("audio_mode") or ("native" if has_audio_direction else "muted")),
    }
    return {
        "package_schema": f"higgsfield-shot-{HIGGSFIELD_PACKAGE_VERSION}",
        "provider": "Higgsfield",
        "provider_fields": provider_fields,
        "shot_id": shot.get("id"),
        "scene_id": shot.get("scene_id"),
        "prompt_file": prompt_file,
        "spatial_map_file": spatial_file,
        "format_plan_file": format_file,
        "camera_path_file": camera_path_file,
        "environment_state_file": environment_file,
        "temporal_lock_file": temporal_file,
        "dynamic_range_file": dynamic_range_file,
        "commercial_direction_file": commercial_direction_file,
        "format": {
            "project_default_aspect_ratio": project.get("aspect_ratio"),
            "format_plan_id": shot.get("format_plan_id"),
            "duration_s": shot.get("duration_s"),
            "capture_fps": (shot.get("temporal_capture") or {}).get("capture_fps"),
            "delivery_fps": (shot.get("temporal_capture") or {}).get("delivery_fps"),
            "shutter_angle": (shot.get("temporal_capture") or {}).get("shutter_angle"),
            "exposure_time_s": (shot.get("temporal_capture") or {}).get("exposure_time_s"),
        },
        "rig_translation": {
            "capture_profile_id": shot.get("capture_profile_id"),
            "shot_size": shot.get("shot_size"),
            "focal_length_mm": shot.get("focal_length_mm"),
            "aperture_t_stop": shot.get("t_stop"),
            "focus_plan": shot.get("focus_plan"),
            "camera_height_cm": shot.get("camera_height_cm"),
            "camera_axis": shot.get("camera_axis"),
            "camera_support": shot.get("camera_support"),
            "camera_move": shot.get("camera_move"),
            "camera_move_primitive": (shot.get("camera_move_plan") or {}).get("primitive"),
            "exposure_notes": shot.get("exposure_notes"),
            "dynamic_range_plan": shot.get("dynamic_range_plan"),
        },
        "spatial_translation": {
            "spatial_map_id": shot.get("spatial_map_id"),
            "camera_mark_id": shot.get("camera_mark_id"),
            "subject_mark_ids": shot.get("subject_mark_ids"),
            "anchor_projection": shot.get("anchor_projection"),
            "multi_person_projection": shot.get("multi_person_projection"),
            "dramatic_coverage_plan": shot.get("dramatic_coverage_plan"),
            "subject_environment_integration": shot.get("subject_environment_integration"),
            "depth_order": shot.get("depth_order"),
            "coordinate_system": spatial_payload.get("coordinate_system"),
        },
        "state_lock": {
            "sequence_cluster_id": shot.get("sequence_cluster_id"),
            "sequence_visual_anchor_asset_id": shot.get("sequence_visual_anchor_asset_id"),
            "quality_profile_id": shot.get("quality_profile_id"),
            "character_state_bindings": shot.get("character_state_bindings"),
            "location_state_id": shot.get("location_state_id"),
            "prop_state_bindings": shot.get("prop_state_bindings"),
            "environmental_state_id": shot.get("environmental_state_id"),
            "special_lighting_event_ids": shot.get("special_lighting_event_ids"),
            "format_plan_id": shot.get("format_plan_id"),
            "body_geometry_locks": shot.get("body_geometry_locks"),
            "multi_person_projection": shot.get("multi_person_projection"),
            "dramatic_coverage_plan": shot.get("dramatic_coverage_plan"),
            "subject_environment_integration": shot.get("subject_environment_integration"),
            "pose_contact_anchor_ids": shot.get("pose_contact_anchor_ids"),
        },
        "reference_bindings": bindings,
        "start_frame_file": start_frame["file"] if start_frame else "",
        "end_frame_file": end_frame["file"] if end_frame else "",
        "action_beats": shot.get("action_beats", []),
        "material_interaction_plan": shot.get("material_interaction_plan"),
        "audio_plan": audio,
        "generation_boundary": {
            "automatic_platform_call": False,
            "credits_consumed_by_export": False,
            "operator_action": "Upload the listed files, bind the suggested handles, paste the prompt, apply settings, then generate.",
        },
        "runtime_checks": [
            "Confirm the currently selected Higgsfield model accepts the listed number and types of references.",
            "Keep required references first if the current model exposes a smaller reference budget.",
            "Do not replace a physical camera path with a zoom, or a pan with an impossible floating translation.",
            "Review the first result at start/25/50/75/end and event-adjacent frames for anatomy, clean surfaces, weather continuity, focus, path and blur direction before spending on more takes.",
            "Reject infinite-HDR clarity: compare the declared highlight clipping, shadow floor and middle-tone anchor against dynamic-range.json.",
        ],
    }


def _package_readme(project: dict[str, Any], shot_count: int, asset_count: int) -> str:
    return f"""# {project.get('title', 'Untitled')} — Higgsfield 生成包

这是一个离线生成的、可移植的人工执行包。它包含 {asset_count} 个已批准参考文件和 {shot_count} 个可执行镜头任务；导出本身没有登录 Higgsfield、调用外部 API 或消耗积分。

## 执行顺序

1. 在 `upload-order.csv` 中按顺序上传 `references/` 内的文件，并使用 `suggested_handle` 命名或绑定资产。
2. 以 `manifest.json.sequences` 为生产顺序进入 `sequences/<cluster-id>/`；先运行 `python verify.py`，再核对 `state-lock.json`。
3. 按 `reference-map.json` 的 rank 加载根身份、当前人物状态、地点状态视图、空间锚点、道具状态和可选桥接关键帧。桥接帧只能补充，不能替代根资产。
4. 核对序列的 `spatial-map.json`、`format-plan.json`、`camera-path.json`、`environment-state.json`、`temporal-lock.json` 与 `dynamic-range.json`；确认画幅、物理机位、环境因果、快门曝光时间、动态模糊方向及亮暗取舍一致，再粘贴含便携 `@handle` 的 `prompt.txt`。
5. 生成一条测试 take，在开始、25%、50%、75%、结束以及接触/闪光/剪辑事件附近检查身份与人体比例、同场景地理、表面纹理爬动、天气连续、焦点、路径和模糊方向；通过后再继续同镜头变体。
6. 将选中的输出按镜头 ID 保存，依 `edit-plan.md` 的原项目剪辑顺序组接。

## 文件职责

- `manifest.json`：包版本、项目设置、镜头和资产索引。
- `upload-order.csv`：全项目一次性资产上传与命名顺序。
- `reference-map.json`：资产 ID、Higgsfield 建议句柄、类型、覆盖范围和便携路径。
- `shot-list.csv`：逐镜入口、提示词、参数与参考清单位置。
- `shots/`：每镜头的提示、设置、空间、格式、相机路径、环境、时间采样、有限动态范围、参考表和执行说明。
- `sequences/`：每个跨镜一致性组的参考、状态、空间、格式、路径、环境、时间锁、动态范围取舍、提示与独立验证器。
- `method-routing.json`：由官方三项 Skill 提炼的任务意图、参考职责、提示预算和能力建议；模型名只作日期化建议。
- `soul-id-prep.json`、`elements-soul-cast-prep.json`：真人素材就绪度和虚构人物参考清单；不训练、不上传，并明确统一身份板不能冒充 5–20 张真人训练照片。
- `product-photoshoot-prep.json`：商品权威事实与十类摄影意图；只输出短意图，不伪造官方后端增强提示。
- `audio-work-orders.json`：逐镜声音、商业节奏和混音职责；不生成音频。
- `production/`：创意圣经、剪辑计划、项目/资产/身份/世界状态/序列/摄影/空间/镜头/连续性清单与全部 QA 审计快照。
- `checksums.sha256`、`verify_package.py`：跨电脑传输后的完整性验证。

## 平台版本说明

本包以 {HIGGSFIELD_KNOWLEDGE_SNAPSHOT} 的官方公开资料为适配快照，并按 `{HIGGSFIELD_OFFICIAL_PROFILE_ID}` 硬校验。若当前 UI、模型或字段与该快照不同，请停止执行并更新适配器；禁止猜测、静默删引用或降级。变化只能影响 UI 映射，不能改变剧本、批准资产、镜头职责、连续性或摄影设计。

## 便携性

所有清单都使用 UTF-8、LF 和相对 POSIX 路径，不包含本机用户名或绝对目录。在 macOS、Windows 或 Linux 上解压后，可运行 `python verify_package.py`（Python 3.10+）验证文件。Skill 始终停在本地制作包；是否由人类在平台使用它不属于 Skill 的执行范围。
"""


def _shot_runbook(shot: dict[str, Any]) -> str:
    return f"""# {shot.get('id')} 执行卡

1. 先核对 `spatial-map.json`，再按 `references.csv` 的 rank 顺序加载参考；不得跳过 `required=true`。
2. 确认 `location_shot_view`、`location_three_quarter` 和 `spatial_anchor` 的句柄与文件无误，再粘贴 `prompt.txt` 并按 `settings.json` 配置当前 Cinema Studio。
3. 核对 `format-plan.json` 不含烧入黑边，`camera-path.json` 的起止标记和承托可执行，`temporal-lock.json` 的快门公式与模糊方向一致；再核对 `dynamic-range.json` 明确保护对象、允许溢出的亮部和允许失去细节的暗部。
4. 镜头时长：{shot.get('duration_s')} 秒；机位轴线：{shot.get('camera_axis')}；运动：{shot.get('camera_move')}；环境：{shot.get('environmental_state_id')}。
5. 首条只作校准。若身份比例、皮肤/材质、空间地理、接触关系、天气响应、焦点、动态模糊或有限动态范围取舍错误，停止批量生成并回到对应批准资产或镜头提示修订。
6. 通过后以 `{shot.get('id')}--take-001` 起顺序保存，不覆盖旧 take，并将视频交回 Skill 写入 `takes.json` 做时间 QA。
"""


def _sequence_verifier_script(reference_limit: int) -> str:
    return f'''#!/usr/bin/env python3
"""Verify one exported sequence cluster using only Python 3.10+."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "reference-map.json", "state-lock.json", "spatial-map.json", "format-plan.json",
    "camera-path.json", "environment-state.json", "temporal-lock.json", "dynamic-range.json", "quality-profile.json",
    "sequence-anchor.json", "settings.json", "prompt.txt",
)
OFFICIAL_PROFILE = "cinema-studio-4-seedance-2.5-official-2026-08-27"
BASE_HEADINGS = (
    "GLOBAL STYLE", "SCENE", "CHARACTERS", "LOCATION", "FIRST FRAME AND BLOCKING",
    "OPTICS", "CAMERA", "PHYSICS", "LIGHTING", "AUDIO",
)


def main() -> int:
    failures = [f"missing: {{name}}" for name in REQUIRED if not (ROOT / name).is_file()]
    if not failures:
        reference_map = json.loads((ROOT / "reference-map.json").read_text(encoding="utf-8"))
        settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
        references = reference_map.get("references", [])
        if reference_map.get("official_conformance_profile_id") != OFFICIAL_PROFILE:
            failures.append("reference map official conformance profile mismatch")
        if settings.get("official_conformance_profile_id") != OFFICIAL_PROFILE:
            failures.append("settings official conformance profile mismatch")
        if settings.get("target_workflow") != "cinema-studio-4" or settings.get("target_model") != "seedance-2.5":
            failures.append("settings must target Cinema Studio 4 / Seedance 2.5")
        if len(references) > {reference_limit}:
            failures.append(f"reference count {{len(references)}} exceeds adapter limit {reference_limit}")
        identity_ranks = [item.get("rank") for item in references if item.get("usage") == "identity_inspector_primary"]
        state_ranks = [item.get("rank") for item in references if item.get("usage") == "current_character_state"]
        if state_ranks and (not identity_ranks or min(identity_ranks) > min(state_ranks)):
            failures.append("unified identity inspector must precede character-state references")
        for item in references:
            path = Path(str(item.get("file", "")))
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"unsafe reference path: {{path}}")
            elif not (ROOT.parent.parent / path).is_file():
                failures.append(f"missing reference file: {{path}}")
        prompt = (ROOT / "prompt.txt").read_text(encoding="utf-8")
        lines = [line.strip().rstrip(":") for line in prompt.splitlines() if line.strip()]
        if not lines or lines[0].upper() != "GLOBAL STYLE":
            failures.append("prompt must begin with GLOBAL STYLE")
        shot_headings = [line for line in lines if re.fullmatch(r"Shot [1-9][0-9]*", line)]
        if not shot_headings:
            failures.append("prompt requires at least one numbered Shot heading")
        ordered = []
        for heading in BASE_HEADINGS:
            try:
                ordered.append(next(index for index, line in enumerate(lines) if line.upper() == heading))
            except StopIteration:
                failures.append(f"prompt missing official section: {{heading}}")
        if ordered and ordered != sorted(ordered):
            failures.append("official prompt sections are out of order")
    if failures:
        print("INVALID sequence")
        for failure in failures:
            print(f"- {{failure}}")
        return 1
    print("VALID sequence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _verifier_script() -> str:
    return '''#!/usr/bin/env python3
"""Verify this portable Higgsfield package without third-party dependencies."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKSUMS = ROOT / "checksums.sha256"


def main() -> int:
    if not CHECKSUMS.is_file():
        print("INVALID: checksums.sha256 is missing", file=sys.stderr)
        return 1
    failures = []
    manifest_path = ROOT / "manifest.json"
    conformance_path = ROOT / "official-conformance.json"
    if not manifest_path.is_file() or not conformance_path.is_file():
        failures.append("manifest.json and official-conformance.json are required")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        conformance = json.loads(conformance_path.read_text(encoding="utf-8"))
        expected = "cinema-studio-4-seedance-2.5-official-2026-08-27"
        if manifest.get("official_conformance", {}).get("profile_id") != expected:
            failures.append("manifest official profile mismatch")
        if conformance.get("profile_id") != expected or conformance.get("strict") is not True:
            failures.append("official conformance record mismatch")
        if conformance.get("version_policy") != "snapshot-must-match-or-block":
            failures.append("official conformance version policy mismatch")
    listed = set()
    for raw_line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            expected, relative = raw_line.split("  ", 1)
        except ValueError:
            failures.append(f"malformed checksum line: {raw_line}")
            continue
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            failures.append(f"unsafe path: {relative}")
            continue
        listed.add(candidate.as_posix())
        path = ROOT / candidate
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"checksum mismatch: {relative}")
    present = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.name != "checksums.sha256" and "__pycache__" not in path.parts
    }
    for relative in sorted(present - listed):
        failures.append(f"unlisted file: {relative}")
    if failures:
        print("INVALID package")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"VALID package: {len(listed)} files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def export_higgsfield(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2
    # Give the operator the actionable terminal condition before the deeper
    # cross-manifest audit. A project with no production shot cannot export,
    # even if stale sequence records also need cleanup.
    try:
        early_shots = json.loads((project_dir / "manifests/shots.json").read_text(encoding="utf-8")).get("shots", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        early_shots = None
    if isinstance(early_shots, list) and not any(
        isinstance(shot, dict) and shot.get("status") in HIGGSFIELD_PRODUCTION_STATUSES
        for shot in early_shots
    ):
        print("ERROR: no ready/generated/selected shots are available for Higgsfield export.", file=sys.stderr)
        return 1
    validation = _run_self_validation(project_dir)
    if not validation.get("valid"):
        print("ERROR: project is not exportable; validation failed.", file=sys.stderr)
        for item in validation.get("errors", []):
            print(f"[ERROR {item.get('code')}] {item.get('message')}", file=sys.stderr)
        return 1

    project = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    asset_manifest = json.loads((project_dir / "manifests/assets.json").read_text(encoding="utf-8"))
    cinema_manifest = json.loads((project_dir / "manifests/cinematography.json").read_text(encoding="utf-8"))
    spatial_manifest = json.loads((project_dir / "manifests/spatial.json").read_text(encoding="utf-8"))
    shot_manifest = json.loads((project_dir / "manifests/shots.json").read_text(encoding="utf-8"))
    identity_manifest = json.loads((project_dir / "manifests/identities.json").read_text(encoding="utf-8"))
    world_manifest = json.loads((project_dir / "manifests/world-state.json").read_text(encoding="utf-8"))
    sequence_manifest = json.loads((project_dir / "manifests/sequences.json").read_text(encoding="utf-8"))
    quality_manifest = json.loads((project_dir / "manifests/quality.json").read_text(encoding="utf-8"))
    commercial_source_path = project_dir / "manifests/commercial.json"
    commercial_manifest = json.loads(commercial_source_path.read_text(encoding="utf-8")) if commercial_source_path.is_file() else None
    methods_source_path = project_dir / "manifests/higgsfield-methods.json"
    methods_manifest = json.loads(methods_source_path.read_text(encoding="utf-8")) if methods_source_path.is_file() else None
    assets = {
        asset["id"]: asset
        for asset in asset_manifest.get("assets", [])
        if isinstance(asset, dict) and isinstance(asset.get("id"), str)
    }
    profiles = {
        profile["id"]: profile
        for profile in cinema_manifest.get("profiles", [])
        if isinstance(profile, dict) and isinstance(profile.get("id"), str)
    }
    format_plans = {
        item["id"]: item
        for item in cinema_manifest.get("format_plans", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    spatial_maps = {
        spatial_map["id"]: spatial_map
        for spatial_map in spatial_manifest.get("spatial_maps", [])
        if isinstance(spatial_map, dict) and isinstance(spatial_map.get("id"), str)
    }
    identity_packs = {
        item["id"]: item for item in identity_manifest.get("identity_packs", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    character_states = {
        item["id"]: item for item in identity_manifest.get("character_states", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    location_worlds = {
        item["id"]: item for item in world_manifest.get("location_worlds", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    location_states = {
        item["id"]: item for item in world_manifest.get("location_states", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    prop_states = {
        item["id"]: item for item in world_manifest.get("prop_states", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    environmental_states = {
        item["id"]: item for item in world_manifest.get("environmental_states", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    special_lighting_events = {
        item["id"]: item for item in world_manifest.get("special_lighting_events", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    sequence_clusters = {
        item["id"]: item for item in sequence_manifest.get("sequence_clusters", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    quality_profiles = {
        item["id"]: item for item in quality_manifest.get("project_quality_profiles", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    scene_orders = {
        scene.get("id"): scene.get("order", 0)
        for scene in project.get("scenes", [])
        if isinstance(scene, dict) and isinstance(scene.get("id"), str)
    }
    shots = [
        shot
        for shot in shot_manifest.get("shots", [])
        if isinstance(shot, dict) and shot.get("status") in HIGGSFIELD_PRODUCTION_STATUSES
    ]
    shots.sort(key=lambda shot: (scene_orders.get(shot.get("scene_id"), 0), shot.get("order", 0), shot.get("id", "")))
    shots_by_id = {str(shot.get("id")): shot for shot in shots}
    if not shots:
        print("ERROR: no ready/generated/selected shots are available for Higgsfield export.", file=sys.stderr)
        return 1

    # The ordinary-light integration probe is an internal release gate, not a
    # production reference.  It proves that the backend can integrate the
    # approved identity and location roots, but uploading it would turn a QA
    # diagnostic into a third, competing person/world authority.
    approved_assets = [
        asset
        for asset in assets.values()
        if asset.get("status") == "approved" and asset.get("type") != "live_action_probe"
    ]
    approved_assets.sort(key=lambda asset: (higgsfield_reference_category(str(asset.get("type"))), asset.get("id", "")))
    if not approved_assets:
        print("ERROR: no approved assets are available for Higgsfield export.", file=sys.stderr)
        return 1

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else project_dir / "exports" / "higgsfield"
    )
    if output.exists():
        print(f"ERROR: export target already exists; refusing to overwrite: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = Path(tempfile.mkdtemp(prefix=".higgsfield-export-", dir=output.parent))

    try:
        handles: dict[str, str] = {}
        used_handles: set[str] = set()
        for asset in approved_assets:
            asset_id = str(asset["id"])
            base = higgsfield_handle(str(asset.get("role") or asset_id))
            handle = base
            if handle.casefold() in used_handles:
                handle = higgsfield_handle(asset_id)
            suffix = 2
            while handle.casefold() in used_handles:
                handle = f"{base}-{suffix}"
                suffix += 1
            handles[asset_id] = handle
            used_handles.add(handle.casefold())

        portable_paths: dict[str, str] = {}
        asset_rows: list[dict[str, Any]] = []
        for asset in approved_assets:
            asset_id = str(asset["id"])
            source_relative = str(asset.get("approved_path"))
            source = project_dir / source_relative
            suffix = source.suffix.lower() or ".bin"
            category = higgsfield_reference_category(str(asset.get("type")))
            destination_relative = Path("references") / category / f"{asset_id}{suffix}"
            destination = temp_path / destination_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            portable_path = destination_relative.as_posix()
            portable_paths[asset_id] = portable_path
            asset_rows.append(
                {
                    "asset_id": asset_id,
                    "role": asset.get("role"),
                    "asset_type": asset.get("type"),
                    "category": category,
                    "suggested_handle": handles[asset_id],
                    "file": portable_path,
                    "reference_coverage": asset.get("reference_coverage"),
                    "capture_profile_id": asset.get("capture_profile_id"),
                    "scene_state_id": asset.get("scene_state_id"),
                    "view_role": asset.get("view_role"),
                    "view_side": asset.get("view_side"),
                    "spatial_map_id": asset.get("spatial_map_id"),
                    "primary_anchor_asset_id": asset.get("primary_anchor_asset_id"),
                    "identity_pack_id": asset.get("identity_pack_id"),
                    "character_state_id": asset.get("character_state_id"),
                    "location_world_id": asset.get("location_world_id"),
                    "location_state_id": asset.get("location_state_id"),
                    "root_reference_ids": asset.get("root_reference_ids"),
                    "surface_policy": asset.get("surface_policy"),
                }
            )

        identity_board_files: dict[str, str] = {}
        for pack_id, pack in sorted(identity_packs.items()):
            board = pack.get("reference_board") if isinstance(pack.get("reference_board"), dict) else {}
            if board.get("status") != "ready":
                continue
            inspector_id = str(pack.get("identity_inspector_asset_id") or "")
            if inspector_id not in portable_paths:
                raise ValueError(f"identity pack {pack_id} has no portable unified inspector authority")
            identity_board_files[pack_id] = portable_paths[inspector_id]

        production_files = (
            "project.json",
            "creative-bible.md",
            "edit-plan.md",
            "manifests/assets.json",
            "manifests/cinematography.json",
            "manifests/quality.json",
            "manifests/candidates.json",
            "manifests/reviews.json",
            "manifests/spatial.json",
            "manifests/shots.json",
            "manifests/continuity.json",
            "manifests/identities.json",
            "manifests/world-state.json",
            "manifests/sequences.json",
            "manifests/takes.json",
            "qa/asset-review.md",
            "qa/cinematography-review.md",
            "qa/spatial-review.md",
            "qa/shot-review.md",
            "qa/cross-scene-review.md",
            "qa/proportion-review.md",
            "qa/quality-review.md",
            "qa/environment-review.md",
            "qa/temporal-review.md",
        )
        optional_production_files = []
        if commercial_source_path.is_file():
            optional_production_files.append("manifests/commercial.json")
        if methods_source_path.is_file():
            optional_production_files.append("manifests/higgsfield-methods.json")
        if (project_dir / "qa/commercial-review.md").is_file():
            optional_production_files.append("qa/commercial-review.md")
        if (project_dir / "qa/higgsfield-methods-review.md").is_file():
            optional_production_files.append("qa/higgsfield-methods-review.md")
        for source_relative in (*production_files, *optional_production_files):
            source = project_dir / source_relative
            destination = temp_path / "production" / source_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix == ".json":
                portable_write_json(destination, json.loads(source.read_text(encoding="utf-8")))
            else:
                portable_write_text(destination, source.read_text(encoding="utf-8"))

        shot_rows: list[dict[str, Any]] = []
        per_asset_shots: dict[str, list[str]] = defaultdict(list)
        shot_index: list[dict[str, Any]] = []
        shot_artifacts: dict[str, dict[str, Any]] = {}
        for shot in shots:
            scene_id = str(shot.get("scene_id"))
            shot_id = str(shot.get("id"))
            shot_root = Path("shots") / scene_id / shot_id
            prompt_relative = (shot_root / "prompt.txt").as_posix()
            settings_relative = (shot_root / "settings.json").as_posix()
            spatial_relative = (shot_root / "spatial-map.json").as_posix()
            format_relative = (shot_root / "format-plan.json").as_posix()
            camera_path_relative = (shot_root / "camera-path.json").as_posix()
            environment_relative = (shot_root / "environment-state.json").as_posix()
            temporal_relative = (shot_root / "temporal-lock.json").as_posix()
            dynamic_range_relative = (shot_root / "dynamic-range.json").as_posix()
            commercial_direction_relative = (shot_root / "commercial-direction.json").as_posix() if commercial_manifest and commercial_manifest.get("mode") != "not_applicable" else ""
            references_relative = (shot_root / "references.csv").as_posix()
            runbook_relative = (shot_root / "RUN.md").as_posix()
            (temp_path / shot_root).mkdir(parents=True, exist_ok=True)
            spatial_map = spatial_maps[str(shot.get("spatial_map_id"))]
            bindings = _shot_reference_bindings(
                shot,
                assets,
                profiles,
                spatial_map,
                character_states,
                location_states,
                prop_states,
                handles,
                portable_paths,
            )
            source_prompt = (project_dir / str(shot.get("video_prompt_path"))).read_text(encoding="utf-8")
            portable_write_text(temp_path / prompt_relative, _higgsfield_prompt(source_prompt, bindings))
            spatial_payload = _resolved_shot_spatial_payload(shot, spatial_map, handles)
            portable_write_json(temp_path / spatial_relative, spatial_payload)
            format_plan = format_plans[str(shot.get("format_plan_id"))]
            format_payload = {
                "package_schema": f"higgsfield-format-plan-{HIGGSFIELD_PACKAGE_VERSION}",
                "shot_id": shot_id,
                "format_plan": format_plan,
                "generation_rule": "deliver the declared image area; do not generate black bars into image pixels",
            }
            portable_write_json(temp_path / format_relative, format_payload)
            camera_path_payload = {
                "package_schema": f"higgsfield-camera-path-{HIGGSFIELD_PACKAGE_VERSION}",
                "shot_id": shot_id,
                "spatial_map_id": shot.get("spatial_map_id"),
                "camera_move_plan": shot.get("camera_move_plan"),
                "model_translation_rule": "preserve physical translation, rotation, support inertia, parallax and settle; never substitute zoom for camera travel",
            }
            portable_write_json(temp_path / camera_path_relative, camera_path_payload)
            environment_state = environmental_states[str(shot.get("environmental_state_id"))]
            lighting_events = [
                special_lighting_events[event_id]
                for event_id in shot.get("special_lighting_event_ids", [])
                if event_id in special_lighting_events
            ]
            environment_payload = {
                "package_schema": f"higgsfield-environment-state-{HIGGSFIELD_PACKAGE_VERSION}",
                "shot_id": shot_id,
                "environmental_state": environment_state,
                "special_lighting_events": lighting_events,
                "continuity_rule": "weather and light events must affect depth, exposure, shadows, reflections, skin, hair, wardrobe and surfaces according to their recorded causes",
            }
            portable_write_json(temp_path / environment_relative, environment_payload)
            temporal_payload = {
                "package_schema": f"higgsfield-temporal-lock-{HIGGSFIELD_PACKAGE_VERSION}",
                "shot_id": shot_id,
                "temporal_capture": shot.get("temporal_capture"),
                "motion_blur_plan": shot.get("motion_blur_plan"),
                "action_beats": shot.get("action_beats"),
                "forbidden_artifacts": [
                    "frame-blended double exposure", "ghost limbs", "texture crawling",
                    "rubber geometry", "jelly warping", "blur direction inconsistent with camera and subject motion",
                ],
            }
            portable_write_json(temp_path / temporal_relative, temporal_payload)
            dynamic_range_payload = {
                "package_schema": f"higgsfield-dynamic-range-{HIGGSFIELD_PACKAGE_VERSION}",
                "shot_id": shot_id,
                "plan": shot.get("dynamic_range_plan"),
                "hard_rule": "one finite scene-referred exposure; do not recover every highlight and shadow with local tone mapping or exposure fusion",
            }
            portable_write_json(temp_path / dynamic_range_relative, dynamic_range_payload)
            commercial_direction = _commercial_direction_for_shot(commercial_manifest, shot_id)
            if commercial_direction_relative:
                portable_write_json(
                    temp_path / commercial_direction_relative,
                    {
                        "package_schema": f"higgsfield-commercial-direction-{HIGGSFIELD_PACKAGE_VERSION}",
                        "shot_id": shot_id,
                        **commercial_direction,
                        "translation_rule": "Use only picture-, action-, speed-, sound- and wardrobe/product-relevant facts in prompt.txt; business and QA facts remain in this work order.",
                    },
                )
            settings = _higgsfield_settings(
                project,
                shot,
                bindings,
                prompt_relative,
                spatial_relative,
                spatial_payload,
                format_relative,
                camera_path_relative,
                environment_relative,
                temporal_relative,
                dynamic_range_relative,
                commercial_direction_relative,
            )
            portable_write_json(temp_path / settings_relative, settings)
            portable_write_csv(
                temp_path / references_relative,
                ["rank", "asset_id", "asset_type", "usage", "required", "suggested_handle", "file"],
                bindings,
            )
            portable_write_text(temp_path / runbook_relative, _shot_runbook(shot))
            for binding in bindings:
                per_asset_shots[binding["asset_id"]].append(shot_id)
            row = {
                "scene_id": scene_id,
                "scene_order": scene_orders.get(scene_id, 0),
                "shot_id": shot_id,
                "shot_order": shot.get("order"),
                "status": shot.get("status"),
                "duration_s": shot.get("duration_s"),
                "prompt_file": prompt_relative,
                "settings_file": settings_relative,
                "spatial_map_file": spatial_relative,
                "format_plan_file": format_relative,
                "camera_path_file": camera_path_relative,
                "environment_state_file": environment_relative,
                "temporal_lock_file": temporal_relative,
                "dynamic_range_file": dynamic_range_relative,
                "commercial_direction_file": commercial_direction_relative,
                "references_file": references_relative,
                "runbook_file": runbook_relative,
            }
            shot_rows.append(row)
            shot_index.append({**row, "reference_count": len(bindings)})
            shot_artifacts[shot_id] = {
                "shot": shot,
                "bindings": bindings,
                "spatial_payload": spatial_payload,
                "format_payload": format_payload,
                "camera_path_payload": camera_path_payload,
                "environment_payload": environment_payload,
                "temporal_payload": temporal_payload,
                "dynamic_range_payload": dynamic_range_payload,
                "commercial_direction": commercial_direction,
                "prompt_file": prompt_relative,
                "settings": settings,
            }

        sequence_index: list[dict[str, Any]] = []
        ordered_clusters = sorted(
            sequence_clusters.values(),
            key=lambda cluster: (
                min(
                    (
                        scene_orders.get(shots_by_id.get(shot_id, {}).get("scene_id"), 0),
                        shots_by_id.get(shot_id, {}).get("order", 0),
                    )
                    for shot_id in cluster.get("shot_ids", [])
                    if shot_id in shots_by_id
                )
                if any(shot_id in shots_by_id for shot_id in cluster.get("shot_ids", []))
                else (999999, 999999),
                str(cluster.get("id", "")),
            ),
        )
        for cluster in ordered_clusters:
            cluster_id = str(cluster.get("id"))
            cluster_root = Path("sequences") / cluster_id
            (temp_path / cluster_root).mkdir(parents=True, exist_ok=True)
            cluster_shots = [shots_by_id[shot_id] for shot_id in cluster.get("shot_ids", []) if shot_id in shots_by_id]
            bindings: list[dict[str, Any]] = []
            seen_binding_ids: set[str] = set()
            for cluster_shot in cluster_shots:
                for binding in shot_artifacts[str(cluster_shot.get("id"))]["bindings"]:
                    asset_id = str(binding["asset_id"])
                    if asset_id in seen_binding_ids:
                        continue
                    seen_binding_ids.add(asset_id)
                    bindings.append({**binding, "rank": len(bindings) + 1})
            bridge_frame_id = str(cluster.get("bridge_frame_asset_id") or "")
            if bridge_frame_id and bridge_frame_id not in seen_binding_ids:
                bridge_asset = assets[bridge_frame_id]
                bindings.append(
                    {
                        "rank": len(bindings) + 1,
                        "asset_id": bridge_frame_id,
                        "asset_type": bridge_asset.get("type"),
                        "usage": "bridge_keyframe_supplementary",
                        "required": False,
                        "suggested_handle": handles[bridge_frame_id],
                        "file": portable_paths[bridge_frame_id],
                    }
                )
                seen_binding_ids.add(bridge_frame_id)
            binding_by_id = {str(binding["asset_id"]): binding for binding in bindings}
            reference_order = cluster.get("reference_order") if isinstance(cluster.get("reference_order"), list) else []
            if set(binding_by_id) != set(reference_order):
                missing = sorted(set(reference_order) - set(binding_by_id))
                extra = sorted(set(binding_by_id) - set(reference_order))
                raise ValueError(
                    f"sequence {cluster_id} binding set differs from its locked reference stack; missing={missing}, extra={extra}"
                )
            bindings = [
                {**binding_by_id[asset_id], "rank": rank}
                for rank, asset_id in enumerate(reference_order, start=1)
            ]
            reference_limit = int(cluster.get("reference_limit"))
            if len(bindings) > reference_limit:
                raise ValueError(
                    f"sequence {cluster_id} has {len(bindings)} references, above {cluster.get('target_workflow')} limit {reference_limit}"
                )
            reference_map = {
                "package_schema": f"higgsfield-sequence-reference-map-{HIGGSFIELD_PACKAGE_VERSION}",
                "sequence_cluster_id": cluster_id,
                "target_workflow": cluster.get("target_workflow"),
                "target_model": cluster.get("target_model"),
                "official_conformance_profile_id": cluster.get("official_conformance_profile_id"),
                "reference_limit": reference_limit,
                "reference_count": len(bindings),
                "camera_move_segment_limit": HIGGSFIELD_CAMERA_MOVE_LIMITS[str(cluster.get("target_workflow"))],
                "reference_stack_sha256": cluster.get("reference_stack_sha256"),
                "references": bindings,
            }
            portable_write_json(temp_path / cluster_root / "reference-map.json", reference_map)
            signature = cluster.get("state_signature") if isinstance(cluster.get("state_signature"), dict) else {}
            character_state_records = [
                character_states[state_id]
                for state_id in signature.get("character_state_ids", [])
                if state_id in character_states
            ]
            location_state = location_states.get(signature.get("location_state_id"), {})
            location_world = location_worlds.get(location_state.get("location_world_id"), {})
            prop_state_records = [
                prop_states[state_id]
                for state_id in signature.get("prop_state_ids", [])
                if state_id in prop_states
            ]
            state_lock = {
                "package_schema": f"higgsfield-state-lock-{HIGGSFIELD_PACKAGE_VERSION}",
                "sequence_cluster_id": cluster_id,
                "state_signature": signature,
                "character_states": character_state_records,
                "identity_packs": [
                    identity_packs[state.get("identity_pack_id")]
                    for state in character_state_records
                    if state.get("identity_pack_id") in identity_packs
                ],
                "location_state": location_state,
                "location_world": location_world,
                "prop_states": prop_state_records,
                "multi_person_projections": {
                    str(cluster_shot.get("id")): cluster_shot.get("multi_person_projection")
                    for cluster_shot in cluster_shots
                    if cluster_shot.get("multi_person_projection")
                },
                "dramatic_coverage_plans": {
                    str(cluster_shot.get("id")): cluster_shot.get("dramatic_coverage_plan")
                    for cluster_shot in cluster_shots
                    if cluster_shot.get("dramatic_coverage_plan")
                },
                "subject_environment_integrations": {
                    str(cluster_shot.get("id")): cluster_shot.get("subject_environment_integration")
                    for cluster_shot in cluster_shots
                    if cluster_shot.get("subject_environment_integration")
                },
                "bridge": {
                    "from_sequence_id": cluster.get("bridge_from_sequence_id"),
                    "frame_asset_id": bridge_frame_id,
                    "supplementary_only": True,
                    "may_replace_root_authorities": False,
                },
            }
            portable_write_json(temp_path / cluster_root / "state-lock.json", state_lock)
            spatial_payload = {
                "package_schema": f"higgsfield-sequence-spatial-map-{HIGGSFIELD_PACKAGE_VERSION}",
                "sequence_cluster_id": cluster_id,
                "shots": [
                    shot_artifacts[str(cluster_shot.get("id"))]["spatial_payload"]
                    for cluster_shot in cluster_shots
                ],
            }
            portable_write_json(temp_path / cluster_root / "spatial-map.json", spatial_payload)
            portable_write_json(
                temp_path / cluster_root / "format-plan.json",
                {
                    "package_schema": f"higgsfield-sequence-format-plan-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "shots": [
                        shot_artifacts[str(cluster_shot.get("id"))]["format_payload"]
                        for cluster_shot in cluster_shots
                    ],
                },
            )
            portable_write_json(
                temp_path / cluster_root / "camera-path.json",
                {
                    "package_schema": f"higgsfield-sequence-camera-path-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "shots": [
                        shot_artifacts[str(cluster_shot.get("id"))]["camera_path_payload"]
                        for cluster_shot in cluster_shots
                    ],
                },
            )
            portable_write_json(
                temp_path / cluster_root / "environment-state.json",
                {
                    "package_schema": f"higgsfield-sequence-environment-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "shots": [
                        shot_artifacts[str(cluster_shot.get("id"))]["environment_payload"]
                        for cluster_shot in cluster_shots
                    ],
                },
            )
            portable_write_json(
                temp_path / cluster_root / "temporal-lock.json",
                {
                    "package_schema": f"higgsfield-sequence-temporal-lock-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "shots": [
                        shot_artifacts[str(cluster_shot.get("id"))]["temporal_payload"]
                        for cluster_shot in cluster_shots
                    ],
                },
            )
            portable_write_json(
                temp_path / cluster_root / "dynamic-range.json",
                {
                    "package_schema": f"higgsfield-sequence-dynamic-range-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "shots": [
                        shot_artifacts[str(cluster_shot.get("id"))]["dynamic_range_payload"]
                        for cluster_shot in cluster_shots
                    ],
                    "continuity_rule": "Exposure priority may change only when the recorded light or narrative point of view changes; clipping and shadow floors remain temporally stable within a shot.",
                },
            )
            commercial_direction_file = ""
            if commercial_manifest and commercial_manifest.get("mode") != "not_applicable":
                commercial_direction_file = "commercial-direction.json"
                portable_write_json(
                    temp_path / cluster_root / commercial_direction_file,
                    {
                        "package_schema": f"higgsfield-sequence-commercial-direction-{HIGGSFIELD_PACKAGE_VERSION}",
                        "sequence_cluster_id": cluster_id,
                        "selected_route_id": commercial_manifest.get("selected_route_id"),
                        "commercial_brief": commercial_manifest.get("commercial_brief"),
                        "shot_directions": {
                            str(cluster_shot.get("id")): shot_artifacts[str(cluster_shot.get("id"))]["commercial_direction"]
                            for cluster_shot in cluster_shots
                        },
                        "audio_plan": commercial_manifest.get("audio_plan"),
                        "deliverables": commercial_manifest.get("deliverables"),
                    },
                )
            quality_profile_id = str(cluster.get("quality_profile_id") or "")
            quality_profile = quality_profiles.get(quality_profile_id)
            if not isinstance(quality_profile, dict) or quality_profile.get("status") != "approved":
                raise ValueError(f"sequence {cluster_id} lacks an approved quality Profile")
            portable_write_json(
                temp_path / cluster_root / "quality-profile.json",
                {
                    "package_schema": f"higgsfield-sequence-quality-profile-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "profile": quality_profile,
                    "quality_floor_id": QUALITY_FLOOR_ID,
                    "quality_floor_pixels_in_upload_map": False,
                    "behavior_translation_only": True,
                },
            )
            sequence_anchor_id = str(cluster.get("sequence_visual_anchor_asset_id") or "")
            sequence_anchor_asset = assets.get(sequence_anchor_id)
            if not isinstance(sequence_anchor_asset, dict) or sequence_anchor_asset.get("status") != "approved":
                raise ValueError(f"sequence {cluster_id} lacks an approved sequence visual anchor")
            portable_write_json(
                temp_path / cluster_root / "sequence-anchor.json",
                {
                    "package_schema": f"higgsfield-sequence-anchor-{HIGGSFIELD_PACKAGE_VERSION}",
                    "sequence_cluster_id": cluster_id,
                    "sequence_visual_anchor_asset_id": sequence_anchor_id,
                    "suggested_handle": handles.get(sequence_anchor_id),
                    "file": portable_paths.get(sequence_anchor_id),
                    "quality_profile_id": quality_profile_id,
                    "reference_order": reference_order,
                    "reference_stack_sha256": cluster.get("reference_stack_sha256"),
                    "authority_policy": "supplements-but-never-replaces-identity-location-state-or-spatial-roots",
                },
            )
            source_prompt_parts = [
                (project_dir / str(cluster_shot.get("video_prompt_path"))).read_text(encoding="utf-8")
                for cluster_shot in cluster_shots
            ]
            official_sequence_prompt = _merge_official_sequence_prompt(source_prompt_parts)
            portable_write_text(
                temp_path / cluster_root / "prompt.txt",
                _higgsfield_prompt(official_sequence_prompt, bindings),
            )
            settings = {
                "package_schema": f"higgsfield-sequence-{HIGGSFIELD_PACKAGE_VERSION}",
                "sequence_cluster_id": cluster_id,
                "target_workflow": cluster.get("target_workflow"),
                "target_model": cluster.get("target_model"),
                "official_conformance_profile_id": cluster.get("official_conformance_profile_id"),
                "reference_limit": reference_limit,
                "reference_count": len(bindings),
                "state_signature": signature,
                "shot_ids": cluster.get("shot_ids"),
                "first_keyframe_id": cluster.get("first_keyframe_id"),
                "end_keyframe_id": cluster.get("end_keyframe_id"),
                "bridge_frame_asset_id": bridge_frame_id,
                "quality_profile_id": quality_profile_id,
                "sequence_visual_anchor_asset_id": sequence_anchor_id,
                "reference_stack_sha256": cluster.get("reference_stack_sha256"),
                "format_plan_file": "format-plan.json",
                "camera_path_file": "camera-path.json",
                "environment_state_file": "environment-state.json",
                "temporal_lock_file": "temporal-lock.json",
                "dynamic_range_file": "dynamic-range.json",
                "commercial_direction_file": commercial_direction_file,
                "quality_profile_file": "quality-profile.json",
                "sequence_anchor_file": "sequence-anchor.json",
                "reference_bindings": bindings,
                "generation_boundary": {
                    "automatic_platform_call": False,
                    "credits_consumed_by_export": False,
                },
            }
            portable_write_json(temp_path / cluster_root / "settings.json", settings)
            portable_write_text(temp_path / cluster_root / "verify.py", _sequence_verifier_script(reference_limit))
            sequence_index.append(
                {
                    "sequence_cluster_id": cluster_id,
                    "shot_ids": cluster.get("shot_ids"),
                    "target_workflow": cluster.get("target_workflow"),
                    "reference_count": len(bindings),
                    "reference_limit": reference_limit,
                    "folder": cluster_root.as_posix(),
                }
            )

        upload_rows: list[dict[str, Any]] = []
        category_order = {
            "characters": 10,
            "locations": 20,
            "products": 25,
            "props": 30,
            "looks": 40,
            "frames": 50,
            "key-art": 60,
            "other": 70,
        }
        character_type_order = {
            "character_identity_inspector": 0,
            "character_state": 10,
            "character_face_anchor": 20,
            "character_body_anchor": 21,
            "character_identity_view": 22,
        }
        ordered_asset_rows = sorted(
            asset_rows,
            key=lambda row: (
                category_order.get(str(row["category"]), 99),
                character_type_order.get(str(row["asset_type"]), 50),
                str(row["asset_id"]),
            ),
        )
        for sequence, row in enumerate(ordered_asset_rows, start=1):
            upload_rows.append(
                {
                    "sequence": sequence,
                    "asset_id": row["asset_id"],
                    "asset_type": row["asset_type"],
                    "category": row["category"],
                    "suggested_handle": row["suggested_handle"],
                    "file": row["file"],
                    "used_by_shots": ";".join(sorted(set(per_asset_shots.get(str(row["asset_id"]), [])))),
                }
            )

        portable_write_csv(
            temp_path / "upload-order.csv",
            ["sequence", "asset_id", "asset_type", "category", "suggested_handle", "file", "used_by_shots"],
            upload_rows,
        )
        portable_write_csv(
            temp_path / "shot-list.csv",
            [
                "scene_id", "scene_order", "shot_id", "shot_order", "status", "duration_s",
                "prompt_file", "settings_file", "spatial_map_file", "format_plan_file", "camera_path_file",
                "environment_state_file", "temporal_lock_file", "dynamic_range_file", "commercial_direction_file",
                "references_file", "runbook_file",
            ],
            shot_rows,
        )
        portable_write_json(
            temp_path / "reference-map.json",
            {
                "package_schema": f"higgsfield-reference-map-{HIGGSFIELD_PACKAGE_VERSION}",
                "assets": ordered_asset_rows,
            },
        )
        method_routes = methods_manifest.get("generation_routes", []) if isinstance(methods_manifest, dict) else []
        soul_records = methods_manifest.get("soul_readiness_records", []) if isinstance(methods_manifest, dict) else []
        product_authorities = methods_manifest.get("product_authorities", []) if isinstance(methods_manifest, dict) else []
        product_briefs = methods_manifest.get("product_photoshoot_briefs", []) if isinstance(methods_manifest, dict) else []

        portable_write_json(
            temp_path / "method-routing.json",
            {
                "package_schema": f"higgsfield-method-routing-{HIGGSFIELD_PACKAGE_VERSION}",
                "policy": HIGGSFIELD_METHODS_POLICY,
                "profile_id": HIGGSFIELD_METHOD_PROFILE_ID,
                "official_skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
                "knowledge_snapshot": HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT,
                "routes": method_routes,
                "routing_rules": [
                    "Classify the task before choosing a capability family; product photography is not generic image generation.",
                    "Treat model names as dated advisories and require a human to inspect the current model schema before manual use.",
                    "Bind every reference to one declared role; never fill a reference budget without a production reason.",
                    "Keep model-facing prompts short and visible-fact-only; retain QA, rights, continuity, and reconstruction facts in JSON.",
                    "For image-to-video, the frame carries appearance while the prompt concentrates on motion, performance, camera, light, physics, and sound.",
                ],
                "execution_boundary": dict(HIGGSFIELD_METHOD_EXECUTION_BOUNDARY),
            },
        )

        soul_export_records: list[dict[str, Any]] = []
        for record in soul_records if isinstance(soul_records, list) else []:
            if not isinstance(record, dict):
                continue
            pack_id = str(record.get("identity_pack_id") or "")
            photo_ids = [item for item in record.get("photo_asset_ids", []) if isinstance(item, str)]
            soul_export_records.append(
                {
                    **record,
                    "portable_identity_board_file": identity_board_files.get(pack_id, ""),
                    "portable_photo_files": [portable_paths[item] for item in photo_ids if item in portable_paths],
                }
            )
        portable_write_json(
            temp_path / "soul-id-prep.json",
            {
                "package_schema": f"higgsfield-soul-id-prep-{HIGGSFIELD_PACKAGE_VERSION}",
                "method_source": "higgsfield-soul-id 0.12.0",
                "readiness_records": soul_export_records,
                "applicable_identity_packs": [
                    {**pack, "portable_reference_board_file": identity_board_files.get(str(pack.get("id")), "")}
                    for pack in identity_packs.values() if pack.get("identity_kind") == "real_person"
                ],
                "official_readiness_contract": {
                    "photo_count_min": SOUL_TRAINING_PHOTO_MIN,
                    "photo_count_max": SOUL_TRAINING_PHOTO_MAX,
                    "photo_count_ideal": [SOUL_TRAINING_PHOTO_IDEAL_MIN, SOUL_TRAINING_PHOTO_IDEAL_MAX],
                    "coverage_checks": list(SOUL_COVERAGE_FIELDS),
                    "ideal_resolution": "at least 1024x1024 per source photograph",
                },
                "authority_separation": {
                    "project_identity_authority": "one approved single-solve identity Inspector board plus deterministic crops",
                    "training_readiness_source": "5-20 unique, lawful, consented real photographs",
                    "rule": "The generated Inspector board is continuity authority but is not a substitute for the official varied real-photo training set.",
                },
                "operator_checklist": [
                    "Confirm likeness consent and every source photograph's usage rights.",
                    "Use only single-person, sharp photographs with visible eyes and no heavy filters or sunglasses.",
                    "Cover multiple angles, lighting conditions, expressions, and distances; avoid repeated near-duplicates.",
                    "Keep the unified Inspector board as the film project's identity authority; never let a bridge frame or state image outrank it.",
                ],
                "automatic_upload": False,
                "training_performed": False,
            },
        )
        portable_write_json(
            temp_path / "elements-soul-cast-prep.json",
            {
                "package_schema": f"higgsfield-elements-soul-cast-prep-{HIGGSFIELD_PACKAGE_VERSION}",
                "applicable_identity_packs": [
                    {**pack, "portable_reference_board_file": identity_board_files.get(str(pack.get("id")), "")}
                    for pack in identity_packs.values() if pack.get("identity_kind") == "fictional"
                ],
                "operator_checklist": [
                    "If a human later configures a fictional-character reference, start from the one approved single-solve Inspector board.",
                    "Use its deterministic crops only for inspection or a UI that requests separate views; the unified board remains ground truth.",
                    "Bind the exact persistent character-state reference separately for each sequence.",
                    "Keep emotion, gaze, and action in the shot prompt instead of creating a new identity.",
                ],
                "automatic_upload": False,
            },
        )
        product_export_authorities: list[dict[str, Any]] = []
        for product in product_authorities if isinstance(product_authorities, list) else []:
            if not isinstance(product, dict):
                continue
            reference_ids = [item for item in product.get("reference_asset_ids", []) if isinstance(item, str)]
            product_export_authorities.append(
                {**product, "portable_reference_files": [portable_paths[item] for item in reference_ids if item in portable_paths]}
            )
        product_export_briefs: list[dict[str, Any]] = []
        for brief in product_briefs if isinstance(product_briefs, list) else []:
            if not isinstance(brief, dict):
                continue
            reference_ids = [item for item in brief.get("reference_asset_ids", []) if isinstance(item, str)]
            product_export_briefs.append(
                {**brief, "portable_reference_files": [portable_paths[item] for item in reference_ids if item in portable_paths]}
            )
        portable_write_json(
            temp_path / "product-photoshoot-prep.json",
            {
                "package_schema": f"higgsfield-product-photoshoot-prep-{HIGGSFIELD_PACKAGE_VERSION}",
                "method_source": "higgsfield-product-photoshoot 0.12.0",
                "product_authorities": product_export_authorities,
                "intent_briefs": product_export_briefs,
                "supported_intent_modes_at_snapshot": sorted(PRODUCT_PHOTOSHOOT_MODES),
                "prompt_ownership_rule": (
                    "The package exports product truth plus a short intent brief. It never fabricates or exposes the provider backend's enhanced GPT Image 2 prompt."
                ),
                "quality_rule": (
                    "Geometry, label/copy, logo placement, color, material response, scale, contact, and source traceability must pass before any lifestyle or campaign derivative."
                ),
                "automatic_upload": False,
                "generation_performed": False,
            },
        )
        portable_write_json(
            temp_path / "audio-work-orders.json",
            {
                "package_schema": f"higgsfield-audio-work-orders-{HIGGSFIELD_PACKAGE_VERSION}",
                "method_source": "higgsfield-generate 0.12.0",
                "model_advisory": "seed_audio",
                "model_advisory_is_authority": False,
                "current_schema_check_required": True,
                "shot_audio": [
                    {"shot_id": shot.get("id"), "duration_s": shot.get("duration_s"), "audio": shot.get("audio", {})}
                    for shot in shots
                ],
                "commercial_audio_plan": commercial_manifest.get("audio_plan", {}) if isinstance(commercial_manifest, dict) else {},
                "rhythm_plan": commercial_manifest.get("rhythm_plan", {}) if isinstance(commercial_manifest, dict) else {},
                "rules": [
                    "Music tempo, edit cadence, capture speed, and playback speed must be designed together rather than inferred independently.",
                    "Ambience, Foley, impacts, dialogue, and music remain separate responsibilities before the mix hierarchy is approved.",
                    "An audio reference is an input role; it is not the same as asking a video model to invent audio.",
                ],
                "generation_performed": False,
            },
        )
        portable_write_json(
            temp_path / "manifest.json",
            {
                "package_schema": f"higgsfield-package-{HIGGSFIELD_PACKAGE_VERSION}",
                "knowledge_snapshot": HIGGSFIELD_KNOWLEDGE_SNAPSHOT,
                "official_conformance": {
                    "profile_id": HIGGSFIELD_OFFICIAL_PROFILE_ID,
                    "status": "validated",
                    "source_urls": list(HIGGSFIELD_OFFICIAL_SOURCE_URLS),
                    "prompt_sections": list(VIDEO_PROMPT_HEADERS),
                    "mismatch_policy": "block-no-silent-downgrade",
                },
                "method_fusion": {
                    "profile_id": HIGGSFIELD_METHOD_PROFILE_ID,
                    "official_skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
                    "knowledge_snapshot": HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT,
                    "skills": list(HIGGSFIELD_METHOD_SKILLS),
                    "routing_file": "method-routing.json",
                    "soul_readiness_file": "soul-id-prep.json",
                    "product_photoshoot_file": "product-photoshoot-prep.json",
                    "audio_work_orders_file": "audio-work-orders.json",
                    "execution_boundary": dict(HIGGSFIELD_METHOD_EXECUTION_BOUNDARY),
                },
                "source_schema_version": project.get("schema_version"),
                "source_project_id": project.get("id"),
                "source_project_title": project.get("title"),
                "source_project_updated_at": project.get("updated_at"),
                "aspect_ratio": project.get("aspect_ratio"),
                "motion_baseline": project.get("motion_baseline"),
                "base_capture_profile_id": cinema_manifest.get("base_profile_id"),
                "base_cinematic_treatment_id": cinema_manifest.get("base_treatment_id"),
                "base_format_plan_id": cinema_manifest.get("base_format_plan_id"),
                "target": {
                    "provider": "Higgsfield",
                    "surface": "Cinema Studio 4",
                    "model": "Seedance 2.5",
                    "version_policy": "snapshot-must-match-or-block",
                    "execution": "offline-work-order-only; no platform operation by this Skill",
                },
                "assets": ordered_asset_rows,
                "shots": shot_index,
                "sequences": sequence_index,
                "generation_boundary": {
                    "platform_called": False,
                    "credits_consumed": False,
                    "network_used": False,
                    "cli_installed": False,
                    "account_authenticated": False,
                    "files_uploaded": False,
                    "soul_training_started": False,
                    "generation_jobs_submitted": False,
                },
            },
        )
        portable_write_json(
            temp_path / "official-conformance.json",
            {
                "package_schema": f"higgsfield-official-conformance-{HIGGSFIELD_PACKAGE_VERSION}",
                "profile_id": HIGGSFIELD_OFFICIAL_PROFILE_ID,
                "knowledge_snapshot": HIGGSFIELD_KNOWLEDGE_SNAPSHOT,
                "strict": True,
                "version_policy": "snapshot-must-match-or-block",
                "target": {"workflow": "cinema-studio-4", "model": "seedance-2.5"},
                "official_source_urls": list(HIGGSFIELD_OFFICIAL_SOURCE_URLS),
                "official_skill_methods": {
                    "profile_id": HIGGSFIELD_METHOD_PROFILE_ID,
                    "skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
                    "knowledge_snapshot": HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT,
                    "skills": list(HIGGSFIELD_METHOD_SKILLS),
                    "source_urls": list(HIGGSFIELD_METHOD_SOURCE_URLS),
                    "adoption": "methods-only-offline",
                    "provider_backends_emulated": False,
                },
                "verified_contract": {
                    "prompt_order": list(VIDEO_PROMPT_HEADERS),
                    "sequence_beats": "numbered Shot blocks with explicit action, camera behavior, ending and Hard cut boundaries",
                    "identity_sheet": {
                        "background": "clean neutral plain/white",
                        "top_row": ["full_front", "full_left_profile", "full_right_profile", "full_back"],
                        "bottom_row": ["portrait_front", "portrait_left_profile", "portrait_right_profile", "blank"],
                        "authority_rule": "one single-solve board first; deterministic crops are secondary inspection/upload files",
                    },
                    "location_sheet": ["front_wide", "left_three_quarter_wide", "right_three_quarter_wide", "reverse_wide", "detail_views_as_needed"],
                    "reference_policy": "deliberate role-bound references; do not fill the reference budget without a production reason",
                    "published_capabilities": {
                        "maximum_duration_s": 30,
                        "maximum_native_resolution": "1080p",
                        "aspect_ratio_range": "9:16 through 21:9",
                        "maximum_reference_inputs": 50,
                        "native_audio": True,
                    },
                },
                "operator_preflight": [
                    "Confirm the live Higgsfield UI still offers Cinema Studio 4 and Seedance 2.5 before any upload.",
                    "Confirm the displayed reference, duration, resolution, aspect and audio controls still match this dated profile.",
                    "If any item differs, stop; update and revalidate the Skill instead of silently changing the package.",
                ],
            },
        )
        portable_write_text(temp_path / "README.md", _package_readme(project, len(shots), len(approved_assets)))
        portable_write_text(temp_path / "verify_package.py", _verifier_script())

        forbidden_paths = {str(project_dir), str(Path.home())}
        machine_path_pattern = re.compile(
            r"(?i)(?<![:A-Za-z0-9])/(?:Users|home|Volumes|mnt|media|private|tmp)/|\b[A-Z]:[\\/](?:Users|Documents and Settings|ProgramData|Windows|Temp)[\\/]"
        )
        text_suffixes = {".json", ".csv", ".md", ".txt", ".py", ".sha256"}
        for path in (path for path in temp_path.rglob("*") if path.is_file() and path.suffix.lower() in text_suffixes):
            content = path.read_text(encoding="utf-8")
            if any(token and token in content for token in forbidden_paths) or machine_path_pattern.search(content):
                raise ValueError(
                    f"portable export contains a machine-specific absolute path in {path.relative_to(temp_path).as_posix()}"
                )

        checksum_lines: list[str] = []
        for path in sorted((path for path in temp_path.rglob("*") if path.is_file()), key=lambda item: item.relative_to(temp_path).as_posix()):
            relative = path.relative_to(temp_path).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checksum_lines.append(f"{digest}  {relative}")
        portable_write_text(temp_path / "checksums.sha256", "\n".join(checksum_lines) + "\n")
        temp_path.replace(output)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)
        print(f"ERROR: Higgsfield export failed: {exc}", file=sys.stderr)
        return 2

    print(f"Created portable Higgsfield package: {output}")
    print(f"Shots: {len(shots)}  Approved references: {len(approved_assets)}")
    print("No platform call was made and no Higgsfield credits were consumed.")
    return 0


__all__ = [name for name in globals() if not name.startswith("__")]
