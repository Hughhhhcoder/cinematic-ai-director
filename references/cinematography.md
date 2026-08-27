# v1.6 自适应真人摄影设计

本文件把 Reality Brief、原创 Treatment、格式、环境与逐镜路径组成可执行摄影系统。ImageGen 只模拟可观察结果，不声称真实使用设备或拥有 EXIF。原创语法详见 [cinematic-grammar.md](cinematic-grammar.md)，天气/光效见 [atmosphere-weather.md](atmosphere-weather.md)，运动/时间见 [camera-motion-temporal.md](camera-motion-temporal.md)。

## 三联选择合同

每项摄影选择同时记录：

1. **物理原因**：有效画幅、机位/镜头、曝光、真实光源、环境、快门、承托或管线。
2. **可观察结果**：透视、景深、焦点、高光、阴影、肤色、材料、视差、模糊和局部介质如何表现。
3. **叙事理由**：为何这种观看距离、控制程度、时间采样或妥协属于故事。

品牌、片名、导演名、`cinematic`、`8K` 或“胶片感”不能代替合同。

## Cinematography thesis 与 Treatment

先分析叙事距离、主观性、时代、空间尺度、动作强度、真实光源、肤色/材料、环境、现实等级、精致上限、节奏和情绪弧线。写 `cinematography thesis`：观众站在哪里，摄影机为何能在那里，光/空间/运动/时间怎样服务故事，何时允许覆盖。

`cinematic_treatment` 用十一个轴线保存原创行为。自然主义对白、夜景犯罪、现实恐怖、年代重演、史诗环境、动作惊悚、亲密爱情、精密商业、表演/MV、档案监控只是提问起点，不是预设 LUT。

## Capture circumstance

- `observer_role`：观察者、现场记录者、受控剧组、安保/档案设备或商业棚拍。
- `camera_access`：入口、通路、工作距离、高度与障碍。
- `operator_constraint`：空间、设备、时间和表演的限制。
- `allowed_contingency`：物理原因允许的裁切、遮挡、曝光/焦点妥协。
- `off_frame_context`：画外墙、光源、演员或行动如何影响画内。

所谓“偶然感”必须由上述条件产生，不能统一添加倾斜、手抖、脏镜头或失焦。

## Profile

Profile 保存：

- digital/35mm/16mm/super8、有效成像宽度与可选机身参考。
- 高光过渡、阴影底线、色彩分离、肤色响应、锐度和微反差。
- spherical/anamorphic、焦段策略、对比、焦外、呼吸、畸变、眩光和焦点衰减。
- 曝光评级/偏移、高光与阴影优先级。
- fps/快门基线、承托、惯性与 capture circumstance。
- 合理光源、明暗比、负补光、实景灯和空气介质。
- 白平衡、Log/扫描/印片或显示转换意图。
- 经校准的介质签名或洁净数字回退。

器材型号只能辅助说明；必须同时有可观察成像行为。

## Format gate

每个 Profile 引用一个已批准 `format_plan_id`。格式计划保存捕获画幅、工作框线、交付画幅、裁切/安全区、squeeze/desqueeze、重构、转换和回归规则，且 `baked_black_bars:false`。变形镜头不擅自改变交付画幅。

默认 16:9；其他比例或序列变化必须先获用户批准。未批准格式不得创建候选 Look。

## 光线与环境

每个光源可指认：窗、天空、太阳、火、灯具、屏幕、车灯或明确片场延伸光。记录方向、大小、距离、落点、明暗比、负补光和暗部信息。低照度不等于全局压黑，观察式项目也不能无因变棚拍。

雨雪、雾烟、尘、火、水下、热浪和特殊光事件引用批准的 environment/light manifest。环境影响能见度、反射、肤色、服装、焦点、曝光和声音，不能只做背景特效。

## 有限动态范围与曝光取舍

真实机身和胶片的动态范围再宽也有限。当场景反差超过工作纬度时，摄影必须选择保亮部还是保暗部；降低曝光会换来更多高光余量，同时把更多暗部推到灵敏度/噪声底线以下。每个 Quality Profile 和 Ready 镜头保存：

- `working_latitude_stops` 以及相对 18% 灰的 `upper_latitude_stops / lower_latitude_stops`。
- `scene_contrast_stops_estimate`、`middle_gray_anchor` 和 `exposure_priority`。
- 哪些亮源核心可合理 clipping、哪些外围高光必须 roll off 并保留颜色/形状。
- 哪些无光区域可以落入黑位或噪声底线，不能用灰色 HDR 提亮补回。
- `local_tone_mapping:false`、`multi_exposure_hdr:false` 和叙事理由。

ImageGen 提示把这些行为放在 `FOCUS EXPOSURE AND CONTINGENCY`；Higgsfield 模型提示仍严格保持官方标题顺序，把逐镜取舍写进 `LIGHTING`，不新增平台未规定的自定义段。小灯丝、太阳盘、镜面闪点可以有界溢出；脸、关键道具或剧情信息按批准优先级落在可读中间调。禁止同时要求窗外、灯芯、肤色、黑衣和深处阴影都清晰饱满，也禁止用局部对比/全局 HDR 假装动态范围无限。

物理依据：[ARRI Dynamic Range White Paper](https://www.arri.com/resource/blob/295460/e10ff8a5b3abf26c33f8754379b57442/2022-09-28-arri-dynamic-range-whitepaper-data.pdf)、[Sony VENICE 2](https://pro.sony/en_GB/products/digital-cinema-cameras/venice2)、[KODAK VISION3 500T](https://www.kodak.com/content/pdfs/motion/KODAK-VISION3-500T-5219-7219-brochure.pdf)。型号数字只用于内部设计工作纬度，不作为模型魔法词。

## 运镜与时间

Profile 定义全片运动原则；逐镜 `camera_move_plan` 冻结真实路径。默认 24fps/180°，但每镜仍保存 capture/delivery fps、播放倍率、快门与计算曝光时间。动态模糊由具体摄影机/主体运动和快门产生，不能用装饰性文字替代。

## 三候选 Look Test v1.6

1. 选择同时包含肤色、织物、硬材质、暗部、亮源、环境和空间层次的诊断剧情瞬间。
2. 统一人物 Inspector/当前状态、地点世界/状态视图、主锚点、空间地图、环境状态和 format plan 全部批准。
3. 固定身份、状态、地点、锚点、空间、时间、天气、剧情事件、人物关系与批准格式；不固定像素级构图。
4. A/B/C 是三个完整摄影假设，各用独立 ImageGen `generate`，`derived_from` 为空且不互相引用。
5. 任意两套必须在 camera witness、optics/position、motion/support、lighting/exposure、environment、temporal sampling、format/reframe 中至少三类实质不同。
6. 介质签名只能使用稳定校准项；没有就 `clean_narrative`。
7. 每张分别通过 photographic、authenticity、texture、geometry、live-action-surface 与环境/空间相关门。
8. 隐藏 Profile 和提示盲呈现；用户只批准一项。全拒绝时记录共同失败，新建比较组并阻断下游。

Look Test 不反向成为人物、地点或物件根。

## Base 与覆盖

- `base_profile_id`、`base_treatment_id`、`base_format_plan_id` 必须互相一致并批准。
- scene-group/scene 覆盖要有叙事理由、适用场景与 return rule。
- 焦段、T-stop、焦点或普通机位变化不自动建立新 Profile。
- 每条 Ready 镜头显式冻结 Profile/Treatment/format/environment，不在提示中发明新系统。

## 验收

### 可重建摄影

能近似还原机位、工作距离、高度、路径、有效画幅、焦段、焦平面、曝光、光源、环境、时间采样、模糊与管线。

### 真人表面与人体

同时通过 [photographic-authenticity.md](photographic-authenticity.md)、[image2-clean.md](image2-clean.md) 和 [human-geometry.md](human-geometry.md)。参数正确但仍像 AI、动画、CG/PBR、塑料模特、游戏海报或统一高级剧照，同样硬失败。

## 器材资料的用途

ARRI/Sony/Kodak/Cooke 等官方资料只帮助理解动态范围、有效画幅、光学、曝光和介质行为；不会自动进入模型提示。Higgsfield 的 Cinema Studio/Camera Control 资料用于适配平台支持的引用、路径和控制，不证明内置 ImageGen 会服从同一关键词。
