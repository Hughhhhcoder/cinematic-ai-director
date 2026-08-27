# v1.6 角色匹配身材与轮廓系统

“比例正确”不等于“符合角色”。`proportion_signature` 记录这个人实际长什么样；`role_physique_brief` 记录剧本和选角为什么需要这种身材、哪些特征必须读出来、候选何时淘汰。两者必须同时通过。

## 推导顺序

1. 剧本明确事实：年龄、身高/体型、职业、运动史、健康/营养、阶层、年代、怀孕/伤病等。
2. 叙事功能：威胁、脆弱、速度、力量、优雅、普通可信、时尚展示或舞台表演。
3. 选角/服装意图：轮廓是否需要远景可读，衣服是修饰、隐藏还是改变体态。
4. 用户明确审美要求：例如修长、健美、模特感、舞者线条；不得用含糊的“好身材”代替可观察事实。
5. 合法真人参考中的已批准事实；不从网页陌生人擅自复制身体身份。

## 分类

- `observed_specific`：忠实保留用户提供/已批准人物的独特实际体态。
- `narrative_fit`：普通可信但符合职业、年龄、健康和生活史。
- `aspirational_lean`：题材明确需要的修长比例与清楚轮廓，不等于消瘦或广角拉伸。
- `aspirational_athletic`：均衡运动体态、功能性肌肉、自然腰胯和稳定承重。
- `aspirational_muscular`：明确需要更高肌肉量的角色；体积必须符合训练史、关节和软组织逻辑。
- `fashion_model`：服装展示需要的身高感、腿长印象、肩线和步态；仍保留真实关节与重心。
- `dancer_performer`：线条、活动度、核心控制、足踝/手臂延伸和节奏体态。
- `strength_power`：肩背、骨盆、腿和握持体现力量与质量，不套修长模板。
- `endurance_trained`：跑者、骑行者等耐力体态，肌肉分布、体脂和姿态服从运动类型。
- `deconditioned_story_specific`：剧情明确需要的缺乏训练、病后或生活史体态；不能被默认美化。
- `soft_tissue_transition`：体重、肌肉、孕期、肿胀等跨镜持续变化；骨架身份不变。
- `custom`：上述分类不能准确覆盖时，必须用完整事实和目标定义，不得作为逃避测量的空值。

年龄、残障、体型和健康差异不是缺陷；标准只服从角色与用户意图。不得把所有女性缩腰长腿、所有男性宽肩增肌，也不得因“真实”而故意生成差比例。

## 必填事实

每个 `role_physique_brief` 保存：

- `id / classification / source / narrative_rationale / age_presentation`
- `stature_and_frame`
- `shoulder_waist_hip_relation`
- `muscle_and_fat_distribution`
- `posture_and_gait`
- `wardrobe_silhouette`
- `must_have_traits`
- `candidate_rejection_criteria`
- `quantitative_targets`
- `visual_body_balance`：`target / measurement_basis / upper_body_share_range / lower_body_share_range / perspective_policy / story_exception`。

## 腿身视觉比例门

- 虚构成年主角默认使用 `balanced_four_six`：在水平机位、长工作距离和中性站姿下，功能腰线至地面的视觉份额记录在约 `0.54–0.64`，项目可在此区间内收紧。
- 时尚、舞者、动作或舞台角色确有需要时可使用 `elongated_three_seven` 印象，记录区间为约 `0.60–0.70`；这是包含骨架、自然腰线、服装腰线和姿态的视觉目标，不等于篡改人体骨骼。
- 无叙事理由的“五五分”轮廓是硬失败。真实人物忠实复现、儿童、特殊体态或明确反类型选角可用 `observed_specific/story_exception`，但必须写明原因，不能被系统偷偷美化或贬低。
- `perspective_policy` 固定为 `natural_perspective_only`。低机位、广角、缩小头部、抬高假腰线或拉长小腿不能作为身份比例通过；这些只能是已批准叙事镜头的投影变化，且不得改写根身份。

所有目标驱动分类——`aspirational_lean / aspirational_athletic / aspirational_muscular / fashion_model / dancer_performer / strength_power / endurance_trained`——至少两个可测目标、两个淘汰条件。目标从以下 `standing_height_1.0` 归一化字段中选择，给范围与叙事理由：`head_to_body / shoulder_width / hip_width / torso_length / upper_arm_length / forearm_length / thigh_length / shin_length / arm_span / hand_length / foot_length`。希望强化腿长时必须用统一 Inspector 全身正背面记录的 `thigh_length` 与 `shin_length` 范围，肩腰胯则分别锁定肩、胯和轮廓事实；不得发明未经整板测量的厘米数或用“更漂亮”代替目标。

## 常见角色要求翻译

- “修长、好比例”：腿/躯干视觉关系、头身范围、肩腰胯连续轮廓、自然骨盆、衣物腰线与镜头透视共同定义。
- “健美但自然”：肩背与腿的功能性体积、合理体脂分布、关节不过度细化、放松状态不持续绷肌。
- “模特感”：身高感、肩线、腿长与步态读得出；不能靠超低机位或广角拉伸伪造。
- “舞者”：核心、骨盆、脊柱、足踝、手臂延展和重心转换一致；不是仅做瘦。
- “力量型”：质量、胸背/骨盆/腿的协同和落地反馈；不是单纯加宽肩。
- “普通人物”：具体、可信、非理想化；但四肢比例、承重、衣身分离仍须正确。

## 生成与摄影规则

- 全身正背面使用接近正交的长工作距离、自然机位高度、脚底完整，避免广角/仰拍伪造腿长。
- 身材目标写进身份事实与白底全身生成；不要只在叙事帧临时加“long legs / perfect body”。
- `wardrobe_silhouette` 明确肩线、腰线、裆位、裤长、鞋跟和面料垂坠如何保留角色体态。箱型服装是剧情选择时可用，但必须区分“服装遮挡”与“身体比例变差”。
- 三分之四与侧面验证胸廓、骨盆、臀腿、腹背体积，不把透视缩短当漂移。
- 叙事镜头不得用自动瘦身、广角拉伸、低机位或姿态扭曲替代批准身材。镜头构图可以强调，但不可改变身体事实。

## `physique_fit_qa`

固定检查：

- `narrative_and_casting_fit`
- `quantitative_target_fit`
- `visual_leg_body_balance_fit`
- `silhouette_and_volume_fit`
- `posture_and_gait_fit`
- `wardrobe_silhouette_fit`
- `no_unrequested_body_template`

硬失败包括：目标范围不符、腿/躯干无原因缩短、肩腰胯关系丢失、脊柱/骨盆塌陷、衣服把批准身材误生为另一体型、跨角度体积漂移、用镜头畸变假装比例好、未经声明套用性别化理想身材。

每条 Ready 镜头在 `body_geometry_locks` 中同时保存 `proportion_signature_id`、`role_physique_brief_id`、准确人物状态与投影说明。视频提示的第一帧和时间锁必须重复这两个 ID，防止视频阶段回退成模型默认体态。
