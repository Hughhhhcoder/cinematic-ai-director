# v1.6 正向实拍质量证据系统

本系统不把“实拍感”定义成 `cinematic / photorealistic / 8K / film grain`。一张图必须同时说明它为何像真实摄影、皮肤与材质如何被真实光源记录，以及为什么精致程度符合这段剧本。

## 质量基线与项目 Profile

`clean-observational-live-action-v001` 只保存可迁移的评判行为：

- 摄影机在场有原因，机位可达，画面允许真实拍摄造成的轻微遮挡、焦点或构图妥协。
- 高光形状、大小、方向和亮度能回溯到具体光源几何；不存在为“高级感”添加的脸部小亮点或无来源轮廓光。
- 肤色在额头、眼周、鼻翼、脸颊、下颌与耳朵间连续，不被局部对比或 HDR 塑成雕塑。
- 皮肤、毛发、棉布、毛织物、木、墙漆、玻璃、金属各有独立粗糙度、边缘和反射，不共享一层噪声/脏纹。
- 中间调保留体积，高光自然过渡，暗部不被统一提亮；焦点衰减符合镜头、距离与光圈。
- 动态范围有限：明确保护对象，允许小面积光源核心溢出或无信息阴影落入黑位；窗外、灯芯、人物脸和最深暗部不会同时拥有同等清晰度。
- 布景来自生活/职业/建造因果，表演来自任务；不是摆拍、英雄海报或游戏宣传帧。

该质量基线是 `calibration_only`，`direct_generation_reference:false`。它不能直接进入 ImageGen 引用。每个项目必须建立新的 `project_quality_profile`，按剧本写：

- `capture_circumstance`
- `illumination_contract`
- `skin_response_contract`
- `material_response_contract`
- `tone_contrast_contract`
- `dynamic_range_contract`
- `focus_optics_contract`
- `set_causality_contract`
- `performance_composition_contract`
- `polish_ceiling`
- `live_action_probe_id`：普通光人物—地点融合探针通过后，含人物的 Profile 才能批准。

## 先证实人物能进入真实世界

参数正确不等于像素真实。统一身份 Inspector、地点根、人体比例和摄影计划全部通过后，仍必须以一个普通光、单人、简单任务的 `live_action_probe` 检验人物是否与场景共享投影、光源、焦点、遮挡、接触、色彩污染和有限曝光。探针禁止风格、器材、导演/片名、颗粒、光晕和特殊天气词；两批仍有油光、塑料/游戏表面或 cut-out 感时记录 `backend_realism_blocked`。详见 [live-action-integration.md](live-action-integration.md)。

## 皮肤状态

只允许：

- `natural_dry`：普通干爽皮肤，微弱且连续的来源型反射。
- `normal`：常态皮脂响应，但不能成为均匀油膜。
- `perspiration`：运动、热或压力导致；写明额头、发际、上唇等区域和持续镜头。
- `rain_wet`：雨水路径、滴落、衣发和环境湿润必须一致。
- `submerged`：水下/刚出水的全套物理状态。
- `cosmetic_sheen`：只用于明确妆效/商业需求，写明施加部位、光源与精致理由。

除 `natural_dry / normal` 外必须有 `skin_state_cause` 与有界 `skin_state_regions`。以下始终硬失败：整脸同强度油膜、光源解释不了的孤立亮斑、每一帧移动的油光、塑料/蜡质表皮、肤色断层、边缘彩色描光。

## `live_action_quality_qa`

每张生产图在 thumbnail、fit、100%、200% 检查以下固定项：

1. `photographic_event_plausibility`
2. `skin_specular_topology`
3. `skin_tone_continuity`
4. `eye_hair_and_edge_behavior`
5. `material_response_separation`
6. `material_roughness_independence`
7. `detail_integrity_without_smear`
8. `no_repeating_or_cross_material_artifact`
9. `lighting_and_contact_causality`
10. `finite_dynamic_range_and_exposure_tradeoff`
11. `set_and_object_causality`
12. `performance_observation_not_promo_pose`
13. `brief_polish_fit`
14. `dramatic_coverage_not_spatial_diagram`（两人以上叙事帧）
15. `subject_environment_integration`（所有含人物叙事帧）

每项不仅填 pass/fail，还必须在 `positive_evidence` 记录画面中能看到什么。`material_pairs` 至少比较两种无关材质，并明确 `same_repeating_texture:false`。脸部或两种无关材质出现相同旋涡、鳞片、指纹、细胞纹或低频涂抹，直接 fail。

`dynamic_range_evidence` 还必须记录曝光优先级、中间调锚点、可观察的亮部损失/roll-off、可观察的暗部底线/损失，并固定 `global_tone_mapping_detected:false`。若每个亮暗层都被局部提亮、锐化和“看清”，即使没有 clipping 也必须 fail。

两人以上叙事帧还要记录 coverage role、观看者位置、裁切地标、前景/焦点人物、相交视线和动作节拍。空间正确但人物全身等距对称列队，或演员只是“站在那里证明位置”，直接 fail。含人物帧必须记录人物怎样共享场景光线、空气介质、焦点/遮挡、接触支撑、材质/色彩传播和边缘行为；任何 cut-out、单独美容灯、独立 HDR/锐化或游戏关卡感直接 fail。

## 提示编译

`image2-live-action-evidence-v1.6` 只编译六段：

1. `PHOTOGRAPHIC EVENT`
2. `APPROVED IDENTITY WORLD AND STATE`
3. `PHYSICAL CAMERA AND BLOCKING`
4. `SOURCE LIGHT AND MATERIAL RESPONSE`
5. `FOCUS EXPOSURE AND CONTINGENCY`
6. `EXCLUSIONS`

排除项最多四组概念：涂抹；蜡/塑料/CG/动画；重复与跨材质纹；轮廓/锐化/HDR 光边。正向部分不使用通用脏化、颗粒、毛孔强化、英雄灯、游戏过场或宣传海报捷径。

## 校准状态

Treatment/环境模块只有两轮各三候选、每轮至少 2/3、总计达到对应阈值才可 `stable`。未完成视觉证据的能力保持 `conditional/blocked` 并回退 `clean_digital_capture`。脚本通过不等于模型视觉能力已校准。
