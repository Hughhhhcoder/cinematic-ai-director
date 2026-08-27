# v1.6 空间锚定场景系统

本文件把场景从“看起来相似的背景图”升级为可供分镜、关键帧和逐镜生成共同引用的固定空间。权威链是：

`location_master → scene state views + primary anchor → spatial map → location plate / Photoboard / keyframe → ready shot → Higgsfield shot package`

## 官方依据与本 Skill 的规范化

- [AI Short Film – Full Prompt Library](https://higgsfield.ai/blog/ai-short-film-youtube-guide) 的地点参考表使用 front、left angled、right angled、reverse wide 和细节覆盖。
- [Characters and Locations](https://higgsfield.ai/blog/consistent-characters-locations) 强调地点、人物和关键物件参考共同维持同一生成中的一致性。
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) 要求明确人物的准确起始位置、朝向、镜头位置和逐时动作。

官方措辞是 angled perspective，并未固定一个精确角度。本 Skill 为离线验证定义 `side_three_quarter_wide`：相对批准正面轴线偏转 30–60°，通常约 45°，且必须看到相邻空间平面、纵深和主锚点。这是可执行内部标准，不冒充平台固定规格。

## 场景状态包

昼夜、天气、环境介质、陈设或损坏状态不同，即使建筑地址相同，也建立不同 `scene_state_id`。每个状态至少包含两张分别调用内置 ImageGen 生成的批准图：

1. `establishing_wide`：无人、空间整体可读、权威正面关系清楚。
2. `side_three_quarter_wide`：从可到达机位偏转 30–60°，显示相邻平面、空间纵深和主锚点。

两图都必须：

- 直接从同一个批准 `location_master` 编辑，而不是从另一张状态图继续编辑。
- 直接引用同一个批准主锚点。
- 锁定墙体、门窗、固定设施、尺度、实景光方向、锚点接地点、尺寸和朝向；天气/空气介质由批准 `environmental_state_id` 提供，不能任意增删。
- 使用不同资产 ID、提示文件和输出文件；裁切、扩图或轻微平移不算独立视角。
- 无人物；它们是空间证据，不是剧情帧。

出现两个以上生产摄影轴线时，扩展为 `front_wide / left_three_quarter_wide / right_three_quarter_wide / reverse_wide`。基础 `side_three_quarter_wide` 可按其 `view_side` 计入左或右覆盖；其他角度仍必须独立生成。

## 动态主锚点

每个场景状态恰好一个 `primary_anchor_asset_id`，且复用一个既有 `prop` 权威职责。

选择优先级：

1. 剧本中稳定、独特、尺度清楚、场内不移动的剧情道具。
2. 有真实生产设计因果的固定陈设，例如工作台、冰箱、售货机、门禁机或路边设施。
3. 没有可信候选时，提出新增陈设的职责、位置和理由，等待用户批准后再创建；不得私自塞入随机物件。

禁止使用人物随身物、重复小物、车辆中的可移动散件、烟雾、光斑、阴影或会在场内移动的物体。`state_locked` 只表示该物体在当前场景状态内完全锁定。

锚点资产使用 `object_multiview`，至少有 `front / side / three_quarter` 和近似宽、深、高。建立图与三分之四图中的接地、比例、朝向和相对墙体位置必须一致。

## 固定坐标系

`manifests/spatial.json` 以锚点底面接触中心为 `(0,0,0)`；单位为 metres，记录精度为 0.1 m。`+Z` 向上，`+X/+Y` 必须同时绑定自然语言现场方向，例如“朝窗墙”“朝走廊门”。

每张空间地图登记：

- 地点母版、场景状态两张基础图、可选多轴图和主锚点。
- 锚点近似尺寸、朝向、选择来源和剧本理由。
- 门窗边界与关键地标。
- 摄影机、人物、道具或动作标记；每个标记有坐标、朝向和相对锚点关系。
- 位移动作的起止标记与路径描述。
- `spatial_qa` 的角度、相邻平面、地理、锚点、机位可达性、尝试次数和升级状态。

坐标是制作近似值，不是假装现场激光测量。若没有测量依据，禁止记录厘米级精度；坐标必须与地标关系同时出现。

## Ready 镜头空间合同

每条 Ready 镜头必须提供：

- `spatial_map_id`：与场景完全一致的批准地图。
- `camera_mark_id`：地图中 `kind=camera` 的可到达机位。
- `subject_mark_ids`：每个 `cast_asset_id` 恰好对应一个人物起始标记。
- `anchor_projection`：`visible | partial | offscreen`、画面区域或画外方向、摄影机到锚点距离、场地固定方向和自然语言关系。
- `depth_order`：从近到远；主锚点即使画外也必须列入。
- 位移动作的 `subject_asset_id / start_mark_id / end_mark_id`，并匹配地图中的路径。

“人物在画面左边”“桌子在镜头右侧”只描述屏幕空间，会在反打时翻转，不能单独通过。必须同时写不随镜头翻转的关系，例如“人物位于锚点 -Y 侧，面朝 +Y 服务门；反打时其屏幕位置改变，但场地坐标不变”。

## 确定性提示段

官方模型提示的 `LOCATION` 段不自由发挥，由清单渲染：地图/状态、锚点原点与朝向、轴线语义、摄影机坐标/朝向/距锚点距离、每个人物坐标/朝向、锚点投影和前后景顺序。手工提示与该段不一致即失败。

Photoboard、关键帧和 location plate 都继承同一 `spatial_map_id`、`scene_state_id`、主锚点及侧面三分之四依赖。画面裁掉锚点不等于解除依赖。

## 空间 QA 与阻断

硬失败包括：

- 三分之四视角小于 30°或大于 60°，看不到相邻平面，或只是裁切/轻微位移。
- 门窗、墙长、设施、材料、光源方向或可达通路跨视图漂移。
- 锚点缺失、重复职责、未批准、悬浮、比例/接地/朝向/位置变化。
- 摄影机标记落在墙内、固定家具内或不可进入区域。
- 只有屏幕左右，没有场地固定方向；画外锚点没有方向或距离。
- Ready 镜头缺人物起点，或位移动作没有清单路径。
- 提示、分镜、关键帧和空间清单互相冲突。

第一次失败只允许一次单变量定向修正。第二次仍有空间硬失败时，空间地图设为 `real_reference_required`，`escalation=real_reference_required`，请求用户提供拥有使用权的实景参考、勘景照片组或平面资料；所有 Look Test、location plate、Photoboard、keyframe、Ready 镜头和导出保持阻断。

## Higgsfield 引用顺序

逐镜导出的职责优先顺序至少包含：

1. 每个人物的统一身份 Inspector、需要时的确定性裁图与当前状态。
2. 需要时的 pose/contact anchor。
3. `location_shot_view`。
4. `location_three_quarter`。
5. `spatial_anchor`。
6. 普通剧情道具及当前状态。
7. 首尾帧、批准 Look 和 supplementary bridge（如有）。

每镜头输出 `spatial-map.json`；`settings.json` 保存地图、机位、人物标记、锚点投影和景深顺序；`camera-path.json` 保存可重建运镜；`prompt.txt` 把资产 ID 确定性替换为便携 `@handle`。导出不登录平台、不上传、不访问网络、不消耗积分。
