# v1.6 项目包与离线清单协议

`scripts/film_project.py` 是权威实现：Python 3.10+、仅标准库、无网络。JSON 使用 UTF-8，文本使用 LF；项目和导出清单只允许相对路径。

## 命令与兼容性

```bash
python3 scripts/film_project.py init --root /parent --title "Film" --slug film
python3 scripts/film_project.py validate /parent/film --json
python3 scripts/film_project.py compile-prompts /parent/film --gate review-foundation-001
python3 scripts/film_project.py build-reference-board /parent/film --identity-pack identity-lead
python3 scripts/film_project.py build-review-board /parent/film --gate review-foundation-001
python3 scripts/film_project.py record-review /parent/film --gate review-foundation-001 --decision approved --selection lookset-base-001=cp-base-a
python3 scripts/film_project.py export-higgsfield /parent/film --output /portable/export
```

所有写命令拒绝覆盖现有版本。退出码：0 成功；1 校验/生产门失败；2 参数或读写失败。v1.0–v1.5 返回 `LEGACY_SCHEMA`，不迁移、不改写。

## 目录

```text
<project>/
├── project.json
├── creative-bible.md
├── edit-plan.md
├── assets/
│   ├── candidates/
│   ├── quality-evidence/
│   ├── review-boards/
│   ├── characters/{identity-inspectors,identity-packs,identity-views,pose-anchors,states}/
│   ├── reference-boards/
│   ├── look-tests/
│   ├── locations/{state-views,plates}/
│   ├── props/
│   ├── storyboards/
│   ├── keyframes/
│   └── key-art/
├── manifests/
│   ├── assets.json
│   ├── candidates.json
│   ├── reviews.json
│   ├── quality.json
│   ├── identities.json
│   ├── world-state.json
│   ├── sequences.json
│   ├── cinematography.json
│   ├── spatial.json
│   ├── shots.json
│   ├── continuity.json
│   └── takes.json
├── prompts/
│   ├── compiled/
│   ├── images/
│   └── video/
├── qa/
│   ├── asset-review.md
│   ├── cinematography-review.md
│   ├── spatial-review.md
│   ├── shot-review.md
│   ├── cross-scene-review.md
│   ├── proportion-review.md
│   ├── quality-review.md
│   ├── environment-review.md
│   └── temporal-review.md
└── exports/higgsfield/
```

## `project.json`

核心值固定为：

```json
{
  "schema_version": "1.6",
  "production_mode": "live-action",
  "capture_policy": "adaptive-live-action-v1.6",
  "static_generator": "builtin-imagegen",
  "video_generation": "package-only",
  "approval_mode": "foundation-and-sequence-gates",
  "aspect_ratio": "16:9",
  "dynamic_range_policy": {
    "mode": "finite_scene_referred",
    "infinite_hdr_forbidden": true,
    "multi_exposure_merge_forbidden": true,
    "rule": "Every photographed frame declares what exposure protects and what highlight or shadow information may be lost."
  },
  "higgsfield_conformance": {
    "official_profile_id": "cinema-studio-4-seedance-2.5-official-2026-08-27",
    "knowledge_snapshot": "2026-08-27",
    "target_workflow": "cinema-studio-4",
    "target_model": "seedance-2.5",
    "strict": true,
    "version_policy": "snapshot-must-match-or-block"
  },
  "candidate_policy": {
    "identity_inspector_initial_count": 1,
    "identity_inspector_max_batches": 1,
    "critical_initial_count": 3,
    "derivative_initial_count": 2,
    "retry_count": 2,
    "max_batches": 2,
    "reviewer": "codex-visual",
    "failed_candidates_visible_by_default": false
  },
  "reproducibility": {
    "backend": "builtin-imagegen",
    "reproducibility_class": "workflow_only",
    "pixel_reproducible": false
  }
}
```

Scene 保存 `capture_profile_id / cinematic_treatment_id / format_plan_id / scene_state_id / environmental_state_id / spatial_map_id / primary_anchor_asset_id`。

## `quality.json`

- `quality_floor_id:clean-observational-live-action-v001`。
- `quality_floors` 只能作 `calibration_only`，且 `direct_generation_reference:false`。
- `project_quality_profiles` 保存 scope、scene/sequence、审批门、Treatment/环境、摄影发生条件、光源、皮肤、材料、中间调/对比、有限 `dynamic_range_contract`、焦点、布景因果、表演/构图和 polish ceiling。
- `calibration_families` 保存两轮三候选的证据；未达发布阈值不得 `stable`，回退 `clean_digital_capture`。

## `assets.json`

关键类型：

- `character_identity_inspector / character_face_anchor / character_body_anchor / character_identity_view / character_state`
- `pose_contact_anchor`
- `location_master / location_variant / location_plate`
- `prop / prop_state / look_test / storyboard / keyframe / key_art`

生产状态：`planned / qualified / approved / rejected / superseded / model_blocked`。候选自身不进入本清单。

每项必须保存：

- ID、role、type、revision、generator/mode、版本化 prompt/candidate/approved path。
- `reference_asset_ids / root_reference_ids / generation_provenance` 与确切顺序/哈希。
- `candidate_set_id / quality_profile_id / approval_gate_id`。
- 精确人物、地点、道具、场景和摄影 Profile 状态 ID。
- `surface_policy / state_delta / localized_story_evidence / material_response_contract / dynamic_range_plan`。
- `photographic_qa / geometry_qa / live_action_quality_qa`；地点空间 QA 位于 `spatial.json`。

`dynamic_range_plan` 对每张摄影资产单独记录有限工作宽容度、场景反差、中灰上下分配、曝光优先级、中间调锚点、高光行为、暗部底线、允许 clipping/暗部损失、`local_tone_mapping:false`、`multi_exposure_hdr:false` 和叙事理由；不能用人物曝光文案污染无人地点。

`live_action_quality_qa` 固定包含四种检查尺度、十三项检查、每项正向证据、无关材质配对、皮肤状态/成因/区域、`dynamic_range_evidence`、verdict、硬失败、Codex reviewer 与时间。用户决定不得出现在 QA。

生成资产策略：

- `image2-live-action-identity-inspector-v1.6`：唯一实际生成的身份策略。
- face/body/identity-view 是 `deterministic-crop`，不能编译为 ImageGen 提示。
- `image2-live-action-character-state-v1.6`
- `image2-live-action-location-v1.6`
- `image2-live-action-object-v1.6`
- `image2-live-action-pose-contact-v1.6`
- `image2-live-action-narrative-v1.6`

统一 `calibration_family:image2-live-action-evidence-v1.6`。提示固定六段，默认禁用通用脏化、渲染和宣传式快捷词。

`generation_provenance` 对内置 ImageGen 固定：

```json
{
  "backend": "builtin-imagegen",
  "reproducibility_class": "workflow_only",
  "pixel_reproducible": false,
  "operation": "generate",
  "prompt_sha256": "<64 hex>",
  "reference_order": ["asset-id"],
  "reference_inputs": [
    {"asset_id": "asset-id", "relative_path": "assets/...png", "sha256": "<64 hex>"}
  ],
  "output": {
    "relative_path": "assets/...png",
    "sha256": "<64 hex>",
    "width_px": 1536,
    "height_px": 1024,
    "color_mode": "RGB",
    "mime_type": "image/png"
  },
  "software_agent": "Codex built-in ImageGen"
}
```

## `candidates.json`

Policy 必须与 `project.json` 一致。每个 candidate set 保存：目标生产资产、tier、状态、operation、审批门、prompt、根引用、selected candidate、选择理由、reviewer/time。`identity_single_solve` 恰好一个 candidate、最多一批；其他 tier 最多两批。

- Critical 首批恰好 3，derivative 首批恰好 2；第二批恰好 2。
- Variant 必须 `operation:generate` 且无 candidate derivative。
- 每张保存文件/提示 SHA-256、根引用顺序、质量 verdict、硬失败和 face/hands/materials/highlights/shadows 诊断框。
- 第二批只在首批全 fail 时允许，并必须命名一个 `changed_variable`。
- `selected` 集合恰好一张且其字节哈希等于目标生产资产活动文件。
- `model_blocked` 只在两批全 fail 时成立，目标资产同步 blocked。

## `reviews.json`

恰好一个 Foundation 门；每个 sequence cluster 恰好一个 Sequence 门。Gate 保存：

- asset/Profile/quality Profile/Treatment/format/comparison/candidate set IDs。
- review overview 与 face/hands/materials/highlights/shadows 诊断板路径。
- `pending / approved / changes_requested` 决定、时间、说明、Look selections 和 affected IDs。

Foundation 批准必须为每个比较组选一套 Profile；门内 `qualified` 记录原子批量晋级。Sequence 批准后批量晋级序列资产和镜头。`changes_requested` 必须有说明和受影响 ID。

## `identities.json`

每个 identity pack 必须保存：

- 一个 `identity_inspector_asset_id`，指向一次 ImageGen 调用生成的完整 4×2 白底权威板。
- 恰好七个 canonical `identity_view_asset_ids`，顺序为 `full_front / full_left_profile / full_right_profile / full_back / portrait_front / portrait_left_profile / portrait_right_profile`；全部必须是统一板的确定性裁图。face/body alias 分别等于 portrait/full-front 裁图。
- `role_physique_brief`：分类、来源、叙事理由、年龄呈现、身高/骨架、肩腰胯、肌肉/脂肪、姿态/步态、服装轮廓、must-have、淘汰条件、量化目标和 `visual_body_balance`。
- `visual_body_balance` 记录 `observed_specific / balanced_four_six / elongated_three_seven / story_exception`、上下身视觉份额、测量基准和固定 `natural_perspective_only`；无理由五五分、低机位或广角假拉腿不能通过。
- `physique_fit_qa` 七项检查、verdict、硬失败、reviewer/time；Inspector 任一格失败即整个人物 `model_blocked`。
- `proportion_signature`、`skeletal_lock`、`immutable_identity`、状态和审批门。

`aspirational_lean / aspirational_athletic / aspirational_muscular / fashion_model / dancer_performer / strength_power / endurance_trained` 至少两个量化目标与两个淘汰条件；实际比例必须落在目标范围。Character state 必须 `preserve_role_physique:true`，只把统一 Inspector 作为身份根，并保存 state delta 与 soft-tissue delta。

`build-reference-board` 验证统一 Inspector，保持固定四列/两排职责顺序，检测中心附近唯一明确的白色横向 gutter，并按记录的实际 `row_split_px` 确定性裁出七张 PNG；不调用 ImageGen、不重绘、不重采样、不覆盖。crop map 记录 gutter 检测证据、裁框和 SHA-256；分隔缺失/歧义或内容跨界会阻断。Inspector `authoritative:true`，裁图为次要检查/上传文件。

## `world-state.json` 与 `spatial.json`

`production_design_dna` 保存年代、经济、建筑、基础设施、色彩来源、材料、标识和老化规则。Location world 冻结拓扑、门窗、固定设施、主锚点、尺度和材料；location/prop/environment/light state 只保存有因果的增量。

每个场景状态至少有独立 `establishing_wide` 与 `side_three_quarter_wide`；多轴再扩展。主锚点接地点为原点，坐标约 0.1 m，+X/+Y 绑定自然语言边界；保存门窗/地标、camera/character/action marks 与路径。所有世界/空间记录带 `approval_gate_id`。

## `cinematography.json`

```json
{
  "schema_version": "1.6",
  "policy": "adaptive-live-action-v1.6",
  "base_profile_id": "",
  "base_treatment_id": "",
  "base_format_plan_id": "",
  "profiles": [],
  "cinematic_treatments": [],
  "format_plans": [],
  "medium_signatures": [],
  "comparison_sets": []
}
```

Profile/Treatment/format/comparison 全部带 `approval_gate_id`。三套 Profile/Look 各自独立，在至少三类摄影行为上实质不同；Foundation 只能批准一个。黑边不得烧入图像。

## `shots.json`

Ready 镜头必须包含：

- `quality_profile_id / sequence_visual_anchor_asset_id`。
- 准确人物/地点/道具/环境/format/capture Profile 状态绑定。
- `body_geometry_locks`：每人同时绑定 `proportion_signature_id / role_physique_brief_id / character_state_id / pose_projection`。
- 两人及以上镜头必须增加 `multi_person_projection`：记录统一机位/整流投影、摄影机高度与俯仰、每人批准身高/场地标记/镜头距离、预期与观察投影比及容差、裁切时采用的身体地标、地平线/消失线、遮挡顺序、共同地面或明确高差，以及 `per_person_scale_transform:false`。
- `spatial_map_id / camera_mark_id / subject_mark_ids / anchor_projection / depth_order`。
- focal/FOV/T-stop/focus/exposure、`camera_move_plan`。
- `dynamic_range_plan`：与当前光线/环境/镜头匹配的有限 scene-referred 曝光取舍；若场景反差大于工作宽容度却未声明亮暗损失，Ready 失败。
- `temporal_capture`，其中 `exposure_time_s = shutter_angle / (360 × capture_fps)`。
- `motion_blur_plan`、动作/表演/物理/材料交互、音频、首尾帧和 sequence。
- `model_prompt_strategy_id:shot-model-v1.6` 与视频提示路径。

完整制作事实必须保存 quality Profile、sequence anchor、角色身材/比例、空间、环境、光材、有限动态范围、相机路径、时间与物理模糊。模型提示只包含会影响画面的事实，并严格使用官方顺序：`GLOBAL STYLE / SCENE / CHARACTERS / LOCATION / FIRST FRAME AND BLOCKING / Shot n / OPTICS / CAMERA / PHYSICS / LIGHTING / AUDIO`。动态范围只写入官方 `LIGHTING`，不得新增非官方标题。

## `sequences.json`

Sequence 保存 state signature、联合视觉锚点、quality Profile、审批门、首尾帧、bridge、目标 adapter、`target_model`、官方 Profile、确切 `reference_order` 与 `reference_stack_sha256`。引用职责顺序固定：统一身份 Inspector → 当前人物状态 → pose anchors → 地点状态/plate/三分之四/空间锚点 → 道具根/状态 → approved Look → sequence anchor → bridge → keyframes → 其余干净根。桥接帧 supplementary only。严格导出固定 Cinema Studio 4 / Seedance 2.5、最多 50 refs、每次生成总时长不超过 30 秒、项目画幅在 9:16–21:9。

## `takes.json`

用户自行生成并交回视频后，take 保存项目相对路径、provider、Skill 未调用平台/未消费积分，以及 start/25%/50%/75%/end、事件样本和十项 temporal QA。QA 由 `codex-visual` 记录，不存用户决定；需要选择时走 review gate。

## Higgsfield 导出

导出包含 `official-conformance.json`、references、shots、sequences、production snapshot、`quality-profile.json`、`sequence-anchor.json`、`dynamic-range.json`、状态/空间/format/path/environment/temporal 文件、SHA-256 与标准库验证器。严格 Profile 固定 `Cinema Studio 4 + Seedance 2.5 / 2026-08-27`，并验证官方提示顺序、最多 50 refs、最长 30 秒、最高原生 1080p、9:16–21:9 和原生音频合同。质量基线照片不进入上传引用表；包内不得出现本机绝对路径，不访问网络。当前 UI 与快照不符时阻断并更新，不静默降级，也不承诺第三方随机像素。
