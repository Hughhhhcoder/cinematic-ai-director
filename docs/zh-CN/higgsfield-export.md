# Higgsfield 离线导出

`export-higgsfield` 将批准后的制作事实转换为人工可执行的逐序列包。它不会登录 Higgsfield、上传文件、调用网络生成接口或消耗积分。

## 序列包内容

```text
sequences/<cluster-id>/
├── reference-map.json
├── state-lock.json
├── spatial-map.json
├── quality-profile.json
├── sequence-anchor.json
├── format-plan.json
├── camera-path.json
├── environment-state.json
├── dynamic-range.json
├── temporal-lock.json
├── settings.json
├── prompt.txt
└── verify.py
```

根包另含 `official-conformance.json`。参考顺序必须把统一 4×2 身份 Inspector 放在当前人物状态之前；七张确定性裁图仅在当前 UI 需要分视图时作为次要文件。地点状态视图、侧面四分之三地点图、空间锚点和可选桥接帧各自保留职责。`@handle`、JSON 清单和提示词必须指向相同状态。

## 官方逐镜提示结构

v1.6 严格绑定 `cinema-studio-4-seedance-2.5-official-2026-08-27`，`prompt.txt` 只能按官方 Seedance 2.5 顺序输出：

```text
GLOBAL STYLE
SCENE
CHARACTERS
LOCATION
FIRST FRAME AND BLOCKING
Shot 1
OPTICS
CAMERA
PHYSICS
LIGHTING
AUDIO
```

多镜头用编号 Shot 与明确 `Hard cut`。完整制作事实仍保留在 JSON 中；质量、状态、空间、人体、环境、时间和动态模糊事实被压缩进对应官方段落，不把内部 QA 标题发送给模型。导出同时阻断超过 50 个参考、超过 30 秒、画幅超出 9:16–21:9、Profile 不匹配或当前 UI 与快照不一致。

`dynamic-range.json` 保存有限工作宽容度、场景反差、曝光优先级、中间调锚点、高光过渡/过曝、阴影底线/损失，以及禁止局部 tone mapping 和多曝光 HDR 的规则。提示词只把可见事实压缩进官方 `LIGHTING`，不会自创平台未规定的段落标题。

## 校验

导出包使用相对路径、UTF-8、LF、确定性排序和 SHA-256。可以在 macOS、Windows 与 Linux 的 Python 3.10+ 环境运行包内 `verify.py`，无需安装第三方库。

生成视频后可将结果交回 Skill，并在 `takes.json` 记录开始、25%、50%、75%、结束与关键接触/灯光事件附近的 QA，检查身份、背景、纹理爬动、闪烁、天气、焦点、路径和动态模糊方向。

严格符合保证的是材料包结构、提示顺序、引用职责和带版本阻断合同，不是第三方随机生成像素。官方依据：[Seedance 2.5](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)、[短片参考流程](https://higgsfield.ai/blog/ai-short-film-youtube-guide)、[真实动作流程](https://higgsfield.ai/blog/realistic-ai-human-movement)、[Cinema Studio 4](https://higgsfield.ai/blog/cinema-studio-4-0)。
