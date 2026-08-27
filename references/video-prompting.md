# v1.6 逐镜视频事实与模型提示

每镜分两层：完整制作事实保存在 JSON；发送给目标视频模型的英文提示只保留会影响画面的支持字段。不要把内部 QA、器材百科、公式推导、导演/片名或长 negatives 发给模型。

## Ready 镜头完整事实

至少保存：

- 叙事任务、时长、motion class、quality Profile/capture Profile/Treatment/format。
- 景别、成像宽度、焦段/FOV、T-stop、焦点与曝光。
- 有限 `dynamic_range_plan`：工作纬度、场景反差估计、中灰锚点、曝光优先级、允许的高光 clipping 和暗部信息损失。
- 空间地图、机位/人物 mark、主锚点投影、depth order 与动作路径。
- 统一 4×2 人物 Inspector、七张确定性裁图、准确人物状态、`role_physique_brief`、`proportion_signature`/skeletal lock、需要时的 pose/contact anchor。
- 地点 world/state/plate、主锚点、道具根/状态。
- environment state、特殊光事件与材料交互。
- 人物 `material_response_contract`：皮肤主光来源/相对尺寸/方向、补光、干湿状态、高光范围、彩光传播、局部对比/色调映射、材质粗糙度与表演策略。
- `camera_move_plan`、`temporal_capture`、`motion_blur_plan`。
- sequence 联合视觉锚点、固定引用栈哈希、首尾关键帧、逐秒动作、表演、物理与音频。

人物状态、地点状态和物件状态必须用精确 ID 绑定，不能只写角色名或自由文本。

## `shot-model-v1.6` 官方 Higgsfield 输出

完整制作事实的字段名不直接发送给模型。导出器按 2026-08-27 官方 Seedance 2.5 指南确定性编译为下面的顺序；不允许添加前言、内部 QA 标题或自定义段名：

```text
GLOBAL STYLE
Original live-action capture behavior, approved format/time facts, quality floor and compact hard locks.

SCENE
The single narrative event, current environment and temporal phase.

CHARACTERS
Portable @handles in the approved reference order: the 4×2 identity Inspector first, then current state, deterministic crops only when the interface needs them, pose/contact evidence and supplementary bridge last. Preserve identity, role physique, body proportions and current state.

LOCATION
Named location state, set-fixed axes and boundaries, camera-to-primary-anchor distance, camera/subject marks, facing, depth order, movement marks, and the anchor's visible/partial/off-screen direction and distance.

FIRST FRAME AND BLOCKING
Exact first pose, weight bearing, shoulder/waist/hip and wardrobe silhouette, hand/foot visibility, contact points, occlusion order, relative height, and the declared first camera mark.

Shot 1
One continuous timed shot. Numbered visible action and performance beats in physical order; end pose/camera mark; `Hard cut` when another numbered Shot follows.

OPTICS
Focal length, T-stop, focus target/transition, exposure priority, natural perspective and causal falloff.

CAMERA
One supported, reachable path for this numbered Shot; support, start/end marks, translation/rotation, speed curve, settle, parallax and motion-blur behavior.

PHYSICS
Gravity, mass, support, contact/collision, inertia, landing, deformation, weather/material response and exact subject/object count. For simple shots, preserve ordinary grounded physics without inventing effects.

LIGHTING
Motivated source geometry, declared finite scene-referred latitude and exposure priority, middle-tone anchor, allowed highlight clipping/roll-off, allowed shadow floor/loss, declared skin state, independent material roughness and approved clean color pipeline. Never make every bright and dark region equally legible; no multi-exposure HDR merge.

AUDIO
Dialogue, room tone, weather, Foley, mechanics and off-screen cues with timing.
```

多镜头序列只重复编号的 `Shot 1 / Shot 2 / ...` 区块；全局、人物、地点、光学、摄影、物理、灯光和音频事实在对应官方段落汇总。每个 Shot 最多一条可重建摄影机路径，切换时明确 `Hard cut`。无人镜头仍保留同一官方标题，但 `CHARACTERS` 与 `LIGHTING` 明确 `no person; skin response is not applicable`，不得凭空加入人物或把皮肤合同复制到空镜。

脚本验证顺序、首行、编号 Shot、最长 30 秒、参考上限、画幅和 Profile；任何不符合都阻断。

## 空间段的确定性

官方 `LOCATION` 段由 `manifests/spatial.json` 渲染，不凭提示作者想象。至少包含：

- 摄影机到主锚点距离。
- 每个人物相对锚点的位置、朝向和 marker ID。
- 运动起止 marker。
- 前中后景顺序。
- 锚点在画面可见/部分/画外；画外时给场地固定方向和距离。

只写“画面左边”不合格；反打会翻转屏幕方向，场地关系不会。

## 人体、环境与时间锁

- 每个人物绑定准确 `character_state_id`、`role_physique_brief_id` 和 `proportion_signature_id`。
- 每镜出现准确 `quality_profile_id` 与 `sequence_visual_anchor_asset_id`。
- 高风险动作必须引用批准 `pose_contact_anchor`。
- 环境段必须出现准确 environment ID；特殊光事件出现准确 event ID。
- 提示出现 capture/delivery fps、快门角和按公式得到的曝光时间。
- camera primitive 和起止 mark 必须与 JSON 一致。
- 模糊 source/amount/direction 必须逐字可核对。

## 模型压缩原则

完整 JSON 可以很详细，`prompt.txt` 只保留当前模型支持且可见的事实：

1. 先保留身份/状态/空间/格式。
2. 再保留动作起止、路径、时间和环境因果。
3. 再保留焦点/曝光/模糊与必要物理。
4. 删除内部 QA、证据等级、品牌百科、重复形容词。

平台不支持的画幅、参考量、首尾帧或运镜段不能被“近似翻译”；导出器应阻断并解释。

## 硬失败

- 身份、比例、关节、手足、状态、地点拓扑或物件结构漂移。
- 路径穿墙、漂浮、zoom 替代 dolly、pan 被写成平移。
- 雨雪/雾烟/火光无来源或不影响材料、人物、曝光和反射。
- 动态模糊方向错误、背景无因融化、帧混合双影、幽灵肢体、果冻形变。
- 画幅黑边烧入图像或未批准重构。
- 动画、插画、CG/PBR、蜡质皮肤、涂抹、重复脏纹理和跨材质复制。
- 皮肤油膜或小亮斑与声明光源/干湿状态不符，彩色边光没有传播到邻近物体，局部对比把脸刻成游戏角色，或人物在运动中维持宣传海报姿态。
- 光源核心、窗外、人物脸、黑衣与深处阴影同时被表现为无噪、无 clipping、同等清晰；或逐帧局部 HDR 导致亮暗边界呼吸和闪烁。
- 角色应有的修长/健美/模特/舞者/力量体态回退为模型默认短腿、箱型躯干或错误衣着轮廓。
- 失败候选、另一状态或桥接帧成为唯一根参考。

## 回片审计

用户把 Higgsfield take 交回后，按 [camera-motion-temporal.md](camera-motion-temporal.md) 在 start/25%/50%/75%/end 和接触/光变/速度/焦点事件附近抽查。结果写入 `takes.json`；QA 由 Codex 记录，用户选择通过门级决定管理。
