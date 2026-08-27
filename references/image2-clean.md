# Image2 洁净真人成像系统 v1.6

“Image2”是本 Skill 对当前 Codex 内置 ImageGen 路径的校准名，不代表可锁定的公开模型快照。工作流可复现，随机像素不可复现。

## 先解决根因

涂抹、鳞片、旋涡、脏阴影、塑料皮肤和动画感通常不是“分辨率不够”，而是通用纹理/美化词扩散到皮肤、织物、墙面、金属与玻璃，或失败候选被连续编辑。固定处理顺序：

1. 删除全局装饰词和通用“电影脏感”。
2. 回到批准的洁净根，执行新的独立生成。
3. 只写身份/比例/空间结构、状态增量、摄影发生条件和真实光材响应。
4. 在缩略图、适配窗口、100%、200% 检查纹理与实拍表面。
5. 第一次失败只删除或改写一个变量；第二次失败 `model_blocked`，请求合法实拍参考。

后期降噪、模糊、降采样、锐化或 JPEG 压缩不能把失败变成通过。

## Surface policies

### `clean_authority`

用于统一身份 Inspector、人物状态中性参考、地点/状态空间图、物件根/状态和姿态接触锚点：

- 不添加颗粒、halation、色差、年代调色、污渍、指纹、毛孔强化或随机磨损。
- 只描述形状、比例、结构、材料类别、颜色和中性拍摄事实。
- 自然细节来自真实光材响应，不用 `8K / ultra-detailed / pores` 放大。

### `clean_narrative`

用于没有校准介质签名的 Look、plate、Photoboard、keyframe 与 key art。允许剧本需要的局部痕迹和环境后果，但不把它们复制到无关材质。

### `calibrated_medium_signature`

只用于叙事图像。必须引用一个同题材两轮独立候选都通过 `live_action_quality_qa` 的 `medium_signature_id`。第一次出现介质伪纹理即删除该变量并退回 `clean_narrative`；不允许靠清理器保留。

## Localized story evidence

持续缺陷必须结构化写明：

```text
Material: navy cotton right sleeve.
Exact region: outer elbow, centered 6 cm above the cuff seam.
Extent: one irregular tear approximately 2 cm long; no surrounding discoloration.
Cause: contact with the broken cabinet edge in shot sh-030-020.
First visible shot: sh-030-030.
Preserve: all other garment panels, skin and props remain identical to the clean authority.
```

`dirty jacket / old room / gritty face / weathered street` 没有边界，禁止进入生产提示。

## 默认禁词与紧凑排除

默认禁止正向使用：

`weathered, worn, gritty, tactile texture, patina, fingerprints, pores, film grain, microtexture, ultra-detailed, 8K`

以下“快捷电影感”词同样默认禁止，因为它们容易把人物推向游戏过场、预告片海报或统一的合成皮肤：

`teal-and-orange, dramatic/cinematic rim light, hero lighting, heroic/perfect composition, premium cinematic, cinematic/glossy skin, HDR look/lighting, volumetric haze, epic lighting, game cinematic, trailer still, award-winning cinematography`

只有明确资产族的两次独立 A/B 都通过并登记可见收益，才可有限启用。提示最多四项紧凑排除：

```text
No painterly or patch smearing.
No animation, CG, wax/plastic, game-cinematic rendering or synthetic glossy skin.
No repeating or copied artifact across unrelated materials.
No rendered outline, oversharpening, clarity/HDR or local-contrast halo.
```

不要把完整 QA 清单发给模型。

## v1.6 提示策略

类型 ID 保持八类：`character-face / character-body / identity-view / character-state / location / object / pose-contact / narrative`，均使用 `image2-live-action-<family>-v1.6`。所有类型统一由确定性编译器输出六段：

1. `PHOTOGRAPHIC EVENT`：摄影者、事件和为何记录；白底身份资产写中性选角/制作记录。
2. `APPROVED IDENTITY WORLD AND STATE`：身份、`role_physique_brief`、比例、地点世界和准确状态事实。
3. `PHYSICAL CAMERA AND BLOCKING`：可达机位、请求视角、空间/人体结构、主锚点与接触。
4. `SOURCE LIGHT AND MATERIAL RESPONSE`：真实光源几何与当前资产实际出现的材质。人物图才发送皮肤状态、肤色连续性和毛发/服装；空地点与纯物件提示明确无人，并禁止注入 skin/hair 词汇，避免模型凭空添加人物或把人类表面语义扩散到场景。
5. `FOCUS EXPOSURE AND CONTINGENCY`：焦点/曝光优先级、角色精致上限及真实拍摄允许的妥协。
6. `EXCLUSIONS`：四组紧凑硬排除。

资产差异来自结构化事实，不靠标题变化：identity-inspector 在一次生成中读取固定 4×2 职责和角色体态；七张 identity-view 只能由 Inspector 确定性裁出，不能再次生图；state 只读取允许增量；location 读取拓扑、状态视角和主锚点；object 读取制造结构/尺寸；pose-contact 读取起点/接触/终点；narrative 读取已批准格式、空间、环境、Profile 和序列锚点。

编译后的模型提示仍遵守注意力预算：中性人物/地点/物件目标 80–180 个英文词，叙事图 140–260 个英文词。精确引用顺序和完整合同保存在清单，模型提示用职责摘要而不重复十几个文件名；白底身份根不会继承项目场景灯光，空地点不会出现 skin/hair，纯物件不会继承人物质量合同。

## 皮肤受光与反游戏过场合同

任何画面只要出现可辨认的人脸或皮肤，`material_response_contract` 就必须在生成前写明：

- `skin_key_source`：世界中真实存在的主光源，而不是“cinematic light”。
- `skin_key_source_size` 与 `skin_key_direction`：光源相对面部的大小和方向，用来约束阴影边缘与高光宽度。
- `skin_fill_sources`：可为空，但不能用未声明的浮动补光美化面部。
- `skin_wetness_state` 与 QA 的 `skin_surface_state` 必须映射到 `natural_dry / normal / perspiration / rain_wet / submerged / cosmetic_sheen`；干燥人物不得出现均匀油膜。
- `skin_specular_behavior`：高光应出现在朝向光源的皮肤平面，宽度与光源大小一致，并随曲面连续变化；不能在额头、鼻梁、脸颊、手臂上复制同一白亮斑。
- `local_contrast_policy` 与 `tone_mapping_policy`：禁止 clarity/HDR 把皱纹、眼袋、鼻唇沟和发丝刻成 CG 凹凸贴图。
- `material_roughness_separation`：皮肤、头发、针织物、墙、金属与釉面各自响应光；不能共享同一种“湿亮脏 shader”。
- `color_contamination_sources`：青、橙、绿等肤色污染必须能追溯到画内或画外的真实光源，并在附近墙面、服装、反射和阴影上同步传播。
- `performance_staging_policy`：动作由任务和重心产生。除非剧本与 Treatment 明确要求，不摆英雄伸手、预告片凝视、海报式中心姿态。

审核时不接受“灯位大概合理”。必须比较可见结果：光源大小对应的高光范围、鼻影/眼窝方向、脸与手臂亮度关系、彩光是否传播、暗部是否仍有真实层级。任一项无法解释即 `skin_specular_source_size_and_extent`、`local_contrast_and_tone_mapping` 或 `no_game_cinematic_render_signature=fail`。

## 确定性参考顺序

1. 每个角色一张批准的统一 4×2 Inspector；七张裁图仅为次要检查/UI 文件。
2. 当前人物状态。
3. 需要时的 pose/contact anchor。
4. 地点根与当前状态视图。
5. 侧面三分之四地点图。
6. 主空间锚点根与当前物件状态。
7. 批准 Look/Profile 对应图。
8. 当前 sequence 联合视觉锚点。
9. 可选上一 sequence 尾帧。

桥接帧排在根与当前状态之后，永远不能独自承担权威。

## 统一正向实拍质量 QA

v1.6 用 `live_action_quality_qa` 合并旧真实性、纹理与实拍表面检查，同时保留独立 `photographic_qa / geometry_qa / spatial_qa`。固定检查：

- 无绘画或局部补丁涂抹。
- 无蜡质、塑料或 CG/PBR 皮肤。
- 眼睛、毛发和轮廓边缘像真实摄影。
- 皮肤高光的大小、方向和覆盖范围能由声明光源解释；肤色在曲面与阴影中过渡连续。
- 局部对比和色调映射没有把五官刻成游戏角色，也没有统一的 HDR/clarity 光边。
- 木、金属、玻璃、织物和皮肤响应彼此独立。
- 不同材质保持各自粗糙度，不共享油亮、脏亮或同一噪声响应。
- 接触阴影与反射有物理因果。
- 无渲染描边和异常锐化光边。
- 无重复或跨材质伪纹理。
- 无游戏过场/预告片海报式渲染签名，人物表演是被观察到的动作而非宣传姿态。
- 精致程度符合 Reality Brief 和项目 quality Profile。

每项必须记录可见的 `positive_evidence`；另比较至少一对无关材质，确认没有相同重复纹。QA 在缩略图、适配窗口、100% 和 200% 都通过，reviewer 必须是 `codex-visual`。用户决定只存在审批门。

任一权威图或脸部在任一尺度失败即硬失败。

## 单变量重试

允许：删除一个介质变量；把模糊 `used/worn` 改为局部证据；恢复批准的统一 Inspector；移除失败/状态链引用。

不允许同时换身份、姿态、机位、光线、环境、状态、构图和排除项；否则无法判断改进来源。

## 负面对照隔离

旧版本脏化提示或高风险“电影感”提示可以保留为文字和已存在的失败证据，但不得再调用 ImageGen 重生，也不得混进候选、盲选或审批卡。校准比较只向用户展示已经各自通过硬门的正向方案；负面对照用于解释规则，不用于让用户从坏图中选“相对不坏”的一张。
