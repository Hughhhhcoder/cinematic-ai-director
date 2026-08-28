# v1.6 后台候选、选片与门级审批

目标是让用户只看值得决定的内容，同时保留失败审计。稳定输出指失败候选不进入生产，不指 ImageGen 每次原始生成必然成功。

## 候选预算

- `identity_single_solve`：每个人物只有一张完整 4×2 白底身份检查板、一次 ImageGen 调用、一个 batch。整板失败即停止该人物；不得对同一身份补生成第二张板，也不得挑选不同板的局部拼成身份。
- `critical`：普通光 `live_action_probe`、关键地点/物件根、每套 Look、序列联合锚点、英雄关键帧；首批 3 张独立生成。
- `derivative`：人物状态、地点角度、普通 Photoboard/关键帧；首批 2 张独立生成。七个身份角度不是候选，而是合格统一板的确定性裁图。
- 全部候选直接引用批准根或同一未决门内的合格根，且 `derived_from_candidate_id:""`。除 `live_action_probe` 外使用 `operation:generate`；探针的三个候选必须分别 `operation:edit` 同一张批准空场景，绝不编辑另一候选。
- 候选 ID 与图片只存在 `candidates.json` 和 `assets/candidates/`，不得占用 `assets.json` 权威职责。

## 内部选片

Codex 对每张候选执行：

1. thumbnail：一眼是否是动画/游戏/宣传帧，比例与构图是否明显错误。
2. fit：摄影事件、空间、光线、姿态和叙事任务是否成立。
3. 100%：脸、眼、发、手、衣物边缘、材质接触、高光和阴影。
4. 200%：补丁涂抹、旋涡/鳞片/细胞纹、跨材质复制、过锐光边和像素污染。

候选必须保存 face/hands/materials/highlights/shadows 诊断框；没有人物时 face/hands 可为空，材料/高光/阴影不可为空。仅一张可 `selected`；其 SHA-256 必须等于目标生产资产的活动文件。

## 第二批

除 `identity_single_solve` 外，只有首批全部 fail 才能开第二批；固定 2 张。`changed_variable` 只记录共同最高优先级失败原因对应的一个改动，例如：

- 删除 `medium signature`；
- 把皮肤主光从模糊“cinematic light”改成具体窗面几何；
- 恢复根身份/地点引用顺序；
- 删除全局 `worn/gritty` 并改为局部剧情证据；
- 修正角色身材 Brief 中一个遗漏的可测轮廓目标。

第二批仍全 fail 时，候选集与目标资产都标记 `model_blocked`。统一身份检查板在第一张整板失败时直接 `model_blocked`，因为继续抽取或修补同一人物会把不稳定身份传播到所有场景。人物/地点权威根请求用户提供有权使用的照片或平面资料；不靠后期清理掩盖。

`live_action_probe` 的两批失败升级为 `backend_realism_blocked`：即使身份和地点分别通过，也不再尝试 Look、特殊天气、多人画面或英雄帧。第二批只能修改一个共同失败变量；不能靠增加 `cinematic`、器材名、颗粒、雾、调色或更强灯光掩盖油光、塑料皮肤、贴图边缘或游戏渲染感。桌台、门窗、固定设施、主锚点、机位或裁切漂移时，优先修正编辑框/底片锁定，不允许用一张新生成的“相似房间”替换权威地点。

## Foundation 门

一次呈现：

- reality/casting/role-physique brief；
- 已通过整板 QA 的统一身份检查板、七张确定性裁图及比例/身材检查；
- 地点多视角与主空间锚点；
- format plan；
- 三套分别通过内部硬门、隐藏 Profile 的 Look；
- 质量 Profile 摘要。

用户批准时必须为每个 comparison set 指定一个 Profile。`record-review` 原子地把门内 `qualified` 资产、Profile、Treatment、format、quality Profile、身份/world/spatial 记录批量提升为 `approved`，其余 Look 变为 `rejected`。不得在 QA 内重复用户决定。

## Sequence 门

每个序列一次呈现联合锚点、当前人物/地点/道具/环境状态、Photoboard、首尾/英雄关键帧、空间图、相机/时间/动态模糊摘要和最终逐镜提示。批准后批量提升门内合格资产与 ready 镜头。

`changes_requested` 必须带 `--affected` 和 `--note`。只使目标及直接依赖失效；无关已通过资产不返工。最后序列批准且验证零错误后可自动离线导出。

## 工具

- `compile-prompts`：从结构化事实确定性编译、版本化、拒绝覆盖。
- `build-review-board`：只解码、裁切、排版原图，不重绘；输出 overview 与五类诊断页。
- `record-review`：原子写入门级决定；失败时回滚全部清单和文件晋级。
