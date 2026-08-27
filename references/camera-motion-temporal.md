# v1.6 摄影机路径、时间采样与动态模糊

自由文本“电影感运镜”不能用于生产。每个 Ready 镜头必须能从空间地图、路径、承托、时间采样和模糊记录近似重建，并能映射到目标 Higgsfield 适配器。

## Camera move plan

`camera_move_plan` 固定记录：

- `primitive`：locked、pan、tilt、roll、dolly_in/out、truck、pedestal、jib_crane、orbit、handheld_follow、gimbal_follow、vehicle_mount 或 drone。
- 真实 `support` 与操作限制。
- 起止摄影机 mark、坐标、朝向和镜头高度。
- 平移距离、旋转角度、持续时间、峰值速度和速度曲线。
- 路径分段、净空、门窗/墙体/演员障碍。
- 地平线与 180°轴线政策。
- 预期视差、主体占画比例、遮挡变化、焦点变化与落稳时间。
- 超现实/VFX 例外及叙事理由；未声明时不得穿墙、漂浮或瞬移。

术语必须精确：

- pan/tilt/roll 是原地旋转，不产生平移视差。
- dolly/truck/pedestal/orbit 是物理位移，必须有路径与视差。
- zoom 改变视角，不改变机位；不能替代 dolly。
- locked 的位移、旋转和峰值速度都为零。
- 路径所需器材必须能进入现场并通过净空。

v1.6 严格目标为 Cinema Studio 4 + Seedance 2.5：每个官方编号 Shot 只映射一条可重建路径；需要第二条路径时新开编号 Shot，并以明确的 `Hard cut` 建立边界。历史适配器 Popcorn 与 Cinema Studio 3 每镜也只允许一条。平台变化时更新带日期的适配器；不支持就阻断，不静默删段。

## Temporal capture

保存：

- `capture_fps`
- `delivery_fps`
- `playback_rate`
- `shutter_angle`
- `exposure_time_s`
- 速度渐变的 `time_map`
- 滚动快门容许模式与理由

曝光时间必须满足：

`exposure_time_s = shutter_angle / (360 × capture_fps)`

24fps/180°约为 1/48 秒。慢动作必须提高拍摄帧率并明确交付帧率/播放倍率；不能只在提示中写 “slow motion”。速度渐变的时间映射要覆盖整个镜头、时间单调、起止一致，且说明动作/声音如何映射。

## Motion blur plan

`motion_blur_plan` 记录：

- `source`：none、camera、subject、both 或 atmosphere。
- `amount`：none、low、moderate 或 high。
- 画面坐标中的方向和运动来源。
- 模糊范围、主体/背景/大气的各自行为。
- 必须保持稳定锐利的参照区。
- 遮挡边缘如何显露/覆盖。
- 叙事原因与禁止伪影。

物理关系：

- locked 机位 + 主体移动：静止背景稳定，模糊沿主体轨迹。
- pan/tilt：背景模糊方向与旋转扫过方向一致；被跟随主体可相对更清楚。
- dolly/truck/orbit：前后景视差和径向/横向位移共同影响模糊；不能变成纯 zoom。
- 短曝光减少模糊并加强断续感；长曝光增加拖影，但不能生成双重轮廓。
- 雨雪/余烬的模糊服从自己的速度和快门，不得复制到皮肤、墙面或服装纹理。

排除：帧混合双影、幽灵肢体、重复脸、果冻形变、背景整体融化、遮挡边缘漏帧、纹理爬动和方向矛盾。不要只写 `cinematic motion blur`。

## 视频提示压缩

生产 JSON 保存完整路径与时间表；模型提示只发送：

- 起止机位和可见路径。
- support、primitive、距离/角度、速度曲线和落稳。
- capture/delivery fps、快门角与计算曝光时间。
- 模糊来源、方向、强度和静止参照区。
- 目标平台能支持的最多运镜段。

内部 QA、公式推导和平台不支持的字段不塞进提示；不支持时直接阻断。

## 回片 Take QA

用户从 Higgsfield 导回视频后，可在 `takes.json` 登记：

- start、25%、50%、75%、end 五个强制样本。
- 接触、光变、速度渐变、焦点转移和剪辑事件附近的额外样本。
- 人物/人体、背景、纹理闪烁、形变、环境流动、曝光、焦点、路径、模糊、滚动快门和首尾匹配。
- 每项人工结果、说明、审批决定和时间戳。

VBench 与 PhyGenBench 只提供检查维度：前者启发主体/背景一致、闪烁和运动平滑；后者启发物理事件出现、顺序和整体自然度。本 Skill 不运行其模型、不虚构自动分数。

## 研究边界

- [Higgsfield Camera Control](https://higgsfield.ai/blog/ai-video-camera-control)：可迁移的是明确路径、速度、镜头与起止状态；具体 UI 和控制能力由版本化适配器决定。
- [Higgsfield Seedance Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide)：可迁移的是在提示顶部明确镜头/时长/画幅与分段动作；模型上限不泛化到全部工作流。
- [VBench](https://github.com/Vchitect/VBench) 与 [PhyGenBench](https://github.com/OpenGVLab/PhyGenBench)：只用于人工 QA 维度。
