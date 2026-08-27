# Higgsfield 离线导出适配 v1.6

本层把零错误的 v1.6 真人项目转换为人工可执行、跨电脑可验证的文件包。它不安装插件、不登录、不上传、不访问网络、不调用平台、不消费积分。

## 运行门

```bash
python3 scripts/film_project.py validate <project> --json
python3 scripts/film_project.py export-higgsfield <project>
python3 <project>/exports/higgsfield/verify_package.py
```

至少一条 ready/generated/selected 镜头；Foundation 与所属 Sequence 门已批准；统一身份检查板及七张确定性裁图、角色身材/比例、人物/地点/道具/环境状态、quality/capture Profile、格式/Treatment、序列联合锚点、空间、有限动态范围、路径、时间、模糊、首尾帧和全部 QA 齐全；参考数量与运镜映射不超过目标适配器。

v1.6 严格导出固定绑定 `cinema-studio-4-seedance-2.5-official-2026-08-27`。这是对 2026-08-27 官方公开资料快照的 100% 结构符合：目标工作流/模型、提示段落顺序、身份/地点参考职责、参考上限、30 秒、1080p 上限、9:16–21:9 与原生音频能力均写入 `official-conformance.json` 和验证器。它不承诺随机生成像素必然成功。实际 UI 任一项与快照不一致时必须停止并更新 Skill，禁止静默降级。

## 包结构

```text
exports/higgsfield/
├── README.md
├── manifest.json
├── official-conformance.json
├── reference-map.json
├── upload-order.csv
├── shot-list.csv
├── soul-id-prep.json
├── elements-soul-cast-prep.json
├── references/<category>/...
├── sequences/<cluster-id>/
│   ├── reference-map.json
│   ├── state-lock.json
│   ├── quality-profile.json
│   ├── sequence-anchor.json
│   ├── spatial-map.json
│   ├── format-plan.json
│   ├── camera-path.json
│   ├── environment-state.json
│   ├── dynamic-range.json
│   ├── temporal-lock.json
│   ├── settings.json
│   ├── prompt.txt
│   └── verify.py
├── shots/<scene>/<shot>/
│   ├── prompt.txt
│   ├── settings.json
│   ├── spatial-map.json
│   ├── format-plan.json
│   ├── camera-path.json
│   ├── environment-state.json
│   ├── dynamic-range.json
│   ├── temporal-lock.json
│   ├── references.csv
│   └── RUN.md
├── production/              # 含 quality/candidates/reviews 审计快照
├── checksums.sha256
└── verify_package.py
```

导出拒绝覆盖。同一已验证项目导出到两个新目录应逐字节一致。

## Reference map

句柄明确区分：

- `identity_inspector_primary`：单张统一身份板，必须排在当前人物状态之前。
- 七张确定性身份裁图只在 UI 明确需要分视图时作为次要检查/上传文件，不能替代或排在 Inspector 之前。
- `current_character_state`。
- `pose_contact_anchor`。
- `location_shot_view / location_three_quarter / location_state_view`。
- `spatial_anchor / root_prop / current_prop_state`。
- `approved_look / start_frame / end_frame`。
- `bridge_keyframe_supplementary`。

根与当前状态优先，桥接靠后且 `required:false`。确定性 reference board 可以随包复制供预览，但不进入权威替代链。

## State、format、path、environment、temporal

- `state-lock.json`：sequence signature、统一身份 Inspector、人物/地点/道具状态与 supplementary bridge 政策。
- `quality-profile.json`：当前项目/序列的摄影事件、皮肤/材质/对比/焦点/精致上限；校准基线照片本身不导出。
- `sequence-anchor.json`：联合视觉锚点、确切引用职责顺序与引用栈 SHA-256。
- `format-plan.json`：捕获/工作/交付画幅、裁切、安全区、squeeze/desqueeze、转换/回归和 no baked black bars。
- `camera-path.json`：起止 marks、primitive、support、坐标/朝向、距离/角度、速度曲线、净空、视差、焦点与落稳。
- `environment-state.json`：天气/介质和特殊光事件的物理/时间事实。
- `dynamic-range.json`：有限 scene-referred 工作宽容度、场景反差估计、中间调锚点、曝光保护对象、允许高光 clipping/rolloff 和阴影沉底；固定禁止局部 tone mapping 与多曝光 HDR。
- `temporal-lock.json`：capture/delivery fps、播放倍率、快门、曝光时间、速度映射、motion blur 与禁止伪影。
- `settings.json`：目标工作流、参考/运镜上限、首尾帧、状态签名和 `automatic_platform_call:false`。

## 本地适配器

2026-08-27 官方快照：

| 工作流/模型 | 参考上限 | Skill 运镜映射 |
|---|---:|---:|
| Popcorn | 4 | 1 |
| Cinema Studio 3 | 9 | 1 |
| Seedance 2.5 | 50 | 每个编号 Shot 一条可重建路径 |
| Cinema Studio 4 | 50 | 每个编号 Shot 一条可重建路径 |

Popcorn/Studio 3 只保留历史适配信息，不是 v1.6 严格导出目标。严格输出只能是 Cinema Studio 4 + Seedance 2.5。官方 Seedance 2.5 提示结构固定为 `GLOBAL STYLE → SCENE → CHARACTERS → LOCATION → FIRST FRAME AND BLOCKING → Shot n → OPTICS → CAMERA → PHYSICS → LIGHTING → AUDIO`；多镜头以编号 Shot 和 `Hard cut` 明确边界。动态范围事实只能压缩进官方 `LIGHTING`，完整计划保存在 JSON，不新增平台未定义标题。超限、超过 30 秒、画幅超出 9:16–21:9、Profile/来源快照不符或运镜无法映射时必须阻断，不能静默丢引用、删路径或改比例。

## Soul ID 与 Elements/Soul Cast

- `identity_kind:real_person` 输出 Soul ID 准备记录，上传前确认肖像同意和使用权。
- `identity_kind:fictional` 输出 Elements/Soul Cast 准备记录。
- 两者都要求一张通过整板 QA 的两排白底 Inspector 作为第一身份输入；当前状态单独绑定。
- 七张确定性裁图只在当前界面要求分视图时上传；统一板始终是 ground truth。
- 文件是准备清单，不代表平台实体已创建。

## 人工执行

1. 运行根验证器和目标 sequence 的 `verify.py`。
2. 查看 state/format/path/environment/dynamic-range/temporal 文件，确认此次只有一个明确 sequence signature。
3. 按 `reference-map.json.rank` 绑定批准文件和 `@handle`；人物必须先绑定 `identity_inspector_primary`，再绑定当前状态。
4. 核对机位、人物起点、角色身材/人体比例/接触、quality Profile、序列联合锚点、空间锚点投影、天气/光事件、曝光保护与亮暗损失、路径和时间。
5. 粘贴 `prompt.txt`，只把当前平台支持字段映射到界面。
6. 首次生成一条校准 take；检查身份/比例、世界状态、材料接触、纹理、天气、路径、焦点和模糊。
7. 用户下载后按 `takes.json` 结构交回审计，文件命名 `<shot-id>--take-###`，不覆盖。

## 便携性

所有文本 UTF-8/LF、确定性排序、相对 POSIX 路径。包内禁止本机绝对路径。`checksums.sha256` 覆盖文件；`verify_package.py` 只用 Python 3.10+ 标准库，可在 macOS、Windows、Linux 验证传输完整性。

## 官方依据与边界

- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)：提示顺序、编号镜头、首帧阻挡、参考输入、最长 30 秒、最高原生 1080p、9:16–21:9 与原生音频。
- [AI Short Film Guide](https://higgsfield.ai/blog/ai-short-film-youtube-guide)：两排人物 reference sheet 与地点正面/左右角度/反向广角职责。
- [Realistic AI Human Movement](https://higgsfield.ai/blog/realistic-ai-human-movement)：人物/地点/起始帧共同引用、编号物理动作与 `@` 句柄。
- [Cinema Studio 4](https://higgsfield.ai/blog/cinema-studio-4-0)：当前 Studio 工作流与多参考能力。

官方没有承诺任何提示都能得到合格像素；本 Skill 能保证的是：若导出成功，包的结构、职责、提示顺序和版本证据与上述快照一致。图像和视频本身仍必须经过人工/视觉 QA。
