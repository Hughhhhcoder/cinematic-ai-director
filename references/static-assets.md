# v1.6 静态资产生产与审批

提示结构见 [image2-clean.md](image2-clean.md)，人体几何见 [human-geometry.md](human-geometry.md)，地点/序列见 [world-sequences.md](world-sequences.md) 和 [spatial-system.md](spatial-system.md)。

## 固定依赖顺序

1. Reality/casting brief、角色身材 brief、quality Profile、有限动态范围合同、world DNA、状态时间线。
2. 一张单次身份解算的大尺寸 3×2 纯白底人物检查板；整板通过后确定性裁出六张检查/上传视图，再建立角色体态门与比例签名。
3. 人物持续状态中性参考；需要时的局部状态近景。
4. 无人物地点 master、物件根与主空间锚点。
5. 地点状态多视角与 spatial map。
6. 以批准空场景为不可变底片的普通光单人 `live_action_probe`；通过前禁用特殊天气、电影风格和多人叙事。
7. 环境状态、特殊光事件、Treatment 与 format approval。
8. 三张独立 Look Test 盲选。
9. 地点 plate、pose/contact anchor、Photoboard、关键帧。
10. 按需 key art/title card。

任何上游未 `qualified` 或不在同一审批门内，下游停止；跨门依赖必须已经批准。

## 中性权威

- 单张人物身份检查板及其六张确定性裁图。
- 人物状态中性参考。
- Location master 与状态地理视图。
- Object root 与中性物件状态。
- Pose/contact anchor。

全部使用 `clean_authority`：自然透视、材料可分、正常白平衡、足够景深，无剧情颗粒、光晕、色差、统一调色、装饰雾或夸张浅景深。每张图仍要有自己的有限 `dynamic_range_plan`；中性白底或勘景图通常降低现场反差，但不能使用局部 HDR 把每个暗缝和亮面都做成同样清晰。人物必须以一次 ImageGen 调用生成完整 3×2 白底检查板，让六个有效格共享同一次身份解算；该板是唯一人物身份权威。六个 PNG 只是从板上无重采样裁出的检查/上传文件。全身格还必须符合 `role_physique_brief`，不能被默认短腿、箱型躯干或错误衣着轮廓替换。

## 摄影化叙事资产

- Look Test
- Location plate
- Photoboard/storyboard
- Keyframe/key art

继承批准的统一身份板/人物状态、地点/道具状态、空间地图、environment、format、Treatment 与 Profile。Storyboard 默认是照片级、可在真实机位和布光下执行的 Photoboard，不是线稿、概念画或 3D previz。

空间主图只证明地理，不能直接成为人物叙事帧。Photoboard、关键帧和 key art 若包含两人以上，必须先冻结 `dramatic_coverage_plan` 与 `subject_environment_integration`：观看者位置、coverage role、景别/裁切地标、前景与焦点人物、相交视线、正在发生的任务动作，以及所有人物共享的光线、空气介质、焦点、遮挡、接触和色调响应。除非有书面叙事理由，禁止把人物全身、等距、对称地摆进地点建立图；这种“空间说明式对峙”即使透视正确也按游戏关卡感硬失败。

表面使用 `clean_narrative`；只有稳定的介质 A/B 记录允许 `calibrated_medium_signature`。

所有含人物叙事资产还有一个更早的像素门：普通光 `live_action_probe`。探针必须独立编辑已批准空场景，不得整帧重生；桌台尺寸/前缘/支撑、门窗、固定设施、锚点、机位和裁切必须通过地标与编辑框外像素对应检查。身份板和地点根可分别合格，但只要人物入景后出现地点漂移、油膜、蜡/塑料皮肤、游戏/CG 模型感、贴图边缘、独立锐化/tone mapping，或不共享场景光线、焦点、遮挡与有限曝光，就停止该身份—地点组合。完整协议见 [live-action-integration.md](live-action-integration.md)。

## 人物

人物身份只调用一次 ImageGen，使用 `image2-live-action-identity-inspector-v1.6.6` 生成一张大尺寸 3×2 纯白底板：

- 上排：`full_front / full_primary_profile / full_back`。
- 下排：`portrait_front / portrait_left_profile / portrait_right_profile`。

全部有效格必须是同一张脸、同一身体、同一身高印象、同一服装鞋履、同一自然干燥皮肤状态和同一中性软光；全身格保持一致比例、完整脚部、水平机位和正常透视。禁止标签、分隔装饰、道具、环境、剧情调色、油光、妆面高光和每格各自变化的光线。

先对整板执行身份、角色身材、人体几何、皮肤/材质和四尺度实拍 QA。任一格失败即停止该人物，不裁图、不生成状态、不进入 Foundation。整板通过后运行：

```bash
python3 scripts/film_project.py build-reference-board <project> --identity-pack <id>
```

命令只接受 8-bit RGB/RGBA PNG，拒绝覆盖；保持声明的三列两排角色顺序，从中心附近唯一明确的白色横向 gutter 记录实际 row split，再确定性裁出六张 PNG，不重绘、不重采样。它记录 gutter 证据、来源 SHA-256、裁框和输出哈希；缺失/歧义分隔、内容跨界或裁掉头发/鞋履直接失败。统一板保持第一身份输入；裁图只用于检查和当前 UI 若要求的分视图上传。人物状态和叙事图仍直接引用统一板，不以裁图或前一状态为根。

板与裁图同时通过 `resolution_qa`：新板原生至少 1536×1024、每列至少 512 px、全身主体至少 560 px 高、脸部至少 300 px 高；不得用插值放大、过锐或压缩伪装清晰度。其他根资产原生长边至少 1536 px，叙事帧至少达到 1920×1080 等效像素覆盖。

## 地点

地点 master 像勘景记录：无人、拓扑/门窗/设施/尺度/材料/通路清楚。每个地点状态独立生成：

- `establishing_wide`
- `side_three_quarter_wide`：相对权威轴偏 30–60°，显示相邻平面、纵深与主锚点。

多轴空间扩展 front/left/right/reverse。所有视图直接回到同一地点根；天气、时间、陈设和损坏是有因果的 state delta。两图都要保持主锚点位置、方向、接地与比例。

## 主空间锚点与物件

每场状态恰好一个稳定、独特、尺度清楚、不会随场移动的主锚点。物件根至少有正面、侧面、三分之四与近似尺寸。若没有可信锚点，先让用户批准新增场景陈设；不拿人物随身物、烟雾、光斑或重复小物凑数。

## Pose/contact anchor

持械、手部接触、奔跑、跌倒、拥抱、打斗等高风险镜头单独制作。明确起点、接触点、终点、承重、解剖侧、力方向、遮挡和关键手部画面占比，同时填写人物皮肤受光、干湿、高光范围、材质粗糙度和任务式表演策略。姿态图通过几何、接触、纹理和实拍表面 QA 后才能进入镜头参考。

## Environment 与叙事图

叙事资产的环境段只引用批准状态：来源、强度、能见度、方向、积累、材质/人物反应、光学影响和当前时间相位。闪电、火光、警灯等必须同步改变曝光、阴影与反射，禁止装饰性体积光。

## ImageGen 候选协议

1. 英文提示先保存到版本化 `prompts/images/`。
2. 新根用 `generate`；参考驱动资产只使用项目内批准根路径。
3. 身份检查板每人物恰好一次调用，失败即停止；其他关键资产首批三张，其余首批两张。探针候选可分别编辑同一权威空场景；任何候选都不得编辑另一个候选。
4. 工具返回后必须用 `view_image` 查看实际像素。
5. 输出写入 `assets/candidates/<set-id>/`，不覆盖旧版本；失败图不占用生产资产职责。
6. 登记提示、参考顺序和输出 SHA-256、尺寸、色彩模式、MIME 与软件代理。
7. 完成统一 `live_action_quality_qa`、有限动态范围、摄影、几何及相关空间/环境 QA，并记录正向证据与诊断裁切区域。
8. 只选一张通过者映射为生产资产 `qualified`；所有失败候选默认隐藏。
9. 用 `build-review-board` 生成门级总览/脸/手/材质/高光/阴影页；Foundation 或 Sequence 明确批准后才批量登记 approved 路径。
10. 旧提示负面对照不重新生成、不进入审批板；只有已经通过内部像素硬门的正向候选才可展示或盲选。

## 审批板

```text
Gate ID / foundation or sequence
Reality, casting, role-physique and quality Profile summary
Selected production asset IDs and hidden-failure count
Inspector-first or sequence reference stack in exact order + SHA-256
Character/location/prop/environment/format/Profile IDs
Proportion signature / role physique / pose-contact anchor when relevant
Overview + face/hand/material/highlight/shadow diagnostic pages
Photographic / live-action-quality / geometry / spatial QA evidence
Decision required: approve gate, select one Look Profile, or request scoped changes
```

常规审批次数为一次 Foundation 加每序列一次；不再逐项打断。单帧修改只重建该项和直接依赖。

## 硬失败

- 身份、比例、关节、体型、地点拓扑、设施、锚点或物件结构漂移。
- 动画、插画、CG/PBR、游戏过场、塑料/蜡质皮肤、无来源油亮皮肤、假眼、毛发粘块、织物熔化。
- 绘画/补丁涂抹、低频糊块、旋涡/鳞片/细胞纹、跨材质复制。
- 无来源彩色边光、HDR/clarity 雕刻、皮肤与墙/服装/金属共享同一亮脏响应、英雄海报式姿态。
- 建立图式叙事：人物在宽景中对称列队、没有明确观看者位置、前景层次、焦点主体、相交视线或任务动作。
- 人物与场景的光线、空气介质、焦点/模糊、边缘、接触阴影或色调映射不一致，产生贴图、合成或游戏模型感。
- 把窗外、灯芯、人物肤色、深暗角落全部局部提亮并同等清晰；场景反差超出工作宽容度却不声明任何 clipping 或暗部损失。
- 无来源光、接触/承重/反射错误、环境不影响材料。
- 剧情缺陷超出声明区域。
- 候选源自失败图、另一状态或另一 Look 候选。

统一身份检查板第一次失败即 `model_blocked`。其他资产第一次整批失败只允许一次单变量独立重生；第二批仍失败则 `model_blocked` 并请求合法实拍参考。
