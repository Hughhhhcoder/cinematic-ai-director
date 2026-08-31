# Night Shift — Higgsfield 生成包

这是一个离线生成的、可移植的人工执行包。它包含 19 个已批准参考文件和 1 个可执行镜头任务；导出本身没有登录 Higgsfield、调用外部 API 或消耗积分。

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

本包以 2026-08-27 的官方公开资料为适配快照，并按 `cinema-studio-4-seedance-2.5-official-2026-08-27` 硬校验。若当前 UI、模型或字段与该快照不同，请停止执行并更新适配器；禁止猜测、静默删引用或降级。变化只能影响 UI 映射，不能改变剧本、批准资产、镜头职责、连续性或摄影设计。

## 便携性

所有清单都使用 UTF-8、LF 和相对 POSIX 路径，不包含本机用户名或绝对目录。在 macOS、Windows 或 Linux 上解压后，可运行 `python verify_package.py`（Python 3.10+）验证文件。Skill 始终停在本地制作包；是否由人类在平台使用它不属于 Skill 的执行范围。
