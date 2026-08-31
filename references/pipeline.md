# v1.6 真人电影端到端流程

## 工作模式

- 新剧本：建立完整项目、后台候选池与 Foundation/Sequence 审批链。
- 继续 v1.6：先 `validate`，再从最近的阻断门继续。
- 单项静态资产：仍执行根/状态追溯、角色身材、几何与正向实拍质量 QA。
- 审计：只检查和报告；用户未要求修改时不改变项目。
- Higgsfield 回片：登记 `takes.json`，只做人工时间 QA，不调用平台。
- v1.0–v1.5：只报告 `LEGACY_SCHEMA`，不迁移。

## 阶段门

| 阶段 | 产物 | 通过门 |
|---|---|---|
| 1 剧本拆解 | 场景、人物、物件、环境、动作与状态时间线 | 因果、开始/结束镜头明确 |
| 2 现实、选角与质量 | reality/casting/physique brief + quality Profile + finite dynamic-range contract + world DNA | 角色身材、光材响应、曝光取舍、精致上限、世界规则明确 |
| 3 单次身份解算 | 一张合格高分辨率 3×2 白底身份板 + 六张确定性裁图 | 整板身份、角色身材、比例、几何、原生清晰度、实拍质量通过；任一格失败即停止人物 |
| 4 人物状态 | state authority + delta/soft-tissue delta | 直接追溯统一身份板，骨架/比例保留 |
| 5 地点世界与物件 | location master + prop roots | 拓扑、设施、制造结构、材质基线批准 |
| 6 地点状态与空间 | 多视角、主锚点、spatial map | 空间/表面 QA，环境状态因果成立 |
| 7 实拍融合探针 | 锁定空场景底片的单人普通光 `live_action_probe` | 桌台/门窗/设施/锚点/机位不漂移，人物与地点共享投影、光线、焦点、遮挡、曝光和材质；两批失败即阻断 |
| 8 Treatment 与格式 | cinematic treatment + approved format | 原创可观察行为、无烧入黑边 |
| 9 Foundation | 三套合格 Look/Profile + 身份/地点/格式板 | 一次盲选、整门批量批准 |
| 10 叙事资产 | sequence anchor、plate、Photoboard、pose anchor、首尾帧 | 后台候选通过；状态、几何、环境、格式和空间可追溯 |
| 11 镜头与序列 | shots + sequence clusters + review boards | 路径、时间、模糊、物理、音频完整；逐序列批准 |
| 12 导出/回片 | Higgsfield 包 + 可选 takes | validate 零错误、适配器支持、离线验证通过 |

v1.7 在剧本拆解后、提示编译前加入一层 `higgsfield-methods.json`：先判断任务属于普通/参考/电影静帧/地点图片、严肃/参考/电影级/商业视频、音频、视频分析或商品摄影，再声明每个参考的唯一职责。真人身份另做 5–20 张合法照片的 Soul 就绪度记录，商品另做几何/标签/Logo/颜色/材质/比例事实锁和十类 Product Photoshoot 意图。该层只影响本地规划和导出侧车文件，不执行平台操作。详见 [higgsfield-method-fusion.md](higgsfield-method-fusion.md)。

## 1. 剧本拆解

逐场记录：地点世界/状态、时间、天气/空气介质、特殊光事件、人物进入状态、服装/伤势/软组织变化、物件状态/位置、动作起终点、接触、对白/声音、叙事任务和持续到何时。任何持续事实的变化都是 sequence 边界候选。

## 2. Reality brief 与世界 DNA

Reality brief 必答：人物为何可信；地点为何这样存在；陈设/损坏的成因；摄影机属于谁、能到哪里、有何操作妥协；允许多精致；禁止哪些 AI 先验。

World DNA 必答：年代、经济条件、建筑/公共设施、颜色的真实来源、材料/标识规则与允许老化。它让多地点属于同一现实世界，但不把所有空间套成同一色调或纹理。

## 3. 角色身材、人体几何与洁净根

先按 [role-physique.md](role-physique.md) 建立 `role_physique_brief`，把角色需要的普通、修长、健美、模特、舞者或力量型体态翻译为可观察轮廓、可测范围和淘汰条件。再按 [human-geometry.md](human-geometry.md) 用一次 ImageGen 调用制作完整高分辨率 3×2 白底身份检查板：上排全身正、主侧、背，下排大尺寸脸部正、左、右。整板是唯一身份权威；通过后才确定性裁出六个检查/上传视图，并从全身正背建立 `proportion_signature` 与 `skeletal_lock`。地点与物件根同时使用 `clean_authority`。所有根必须通过 photographic、geometry、`resolution_qa` 与统一 `live_action_quality_qa`。

整板通过后运行：

```bash
python3 scripts/film_project.py build-reference-board <project> --identity-pack <identity-id>
```

命令不再重新排版身份，而是验证统一板，记录中心白色横向 gutter 的实际排界，并无重采样裁出六个角色视图。它不会用数学中线切断偏高的全身排；分隔歧义、内容跨界、裁掉头发/鞋履或原生细节不足会阻断。统一板保持权威，裁图只是检查/上传文件。

## 4. 状态系统

人物、地点和物件状态都直接回到各自根，不从前一状态递归编辑。人物状态始终以统一身份板为第一身份输入，写 `state_delta`；年龄/体重/怀孕/肿胀/肌肉等写 `soft_tissue_delta` 并保持骨架。天气、昼夜、陈设和损坏写地点状态增量。微小缺陷必须在目标分辨率可验收，否则先做局部权威近景或请求合法实拍参考。

## 5. 场景空间与环境

每个地点状态选择唯一固定主锚点，生成独立 `establishing_wide` 与 `side_three_quarter_wide`，必要时扩展多轴视角；建立 0.1 m 场地坐标、机位/人物标记、动作路径和画外锚点关系。

每场显式绑定 `environmental_state_id`。雨雪、雾烟、尘、火、水下、热浪及特殊光事件必须有来源、方向、材料后果、光学影响和时间边界，详见 [atmosphere-weather.md](atmosphere-weather.md)。

## 6. 质量 Profile、Treatment、格式与 Look

在任何 Look 之前，先按 [live-action-integration.md](live-action-integration.md) 生成普通光单人融合探针。它只引用统一身份 Inspector 和一个地点权威，使用简单任务/接触、可达中景、无特殊天气/风格/介质词，并检查皮肤、材质、投影、共享光线、焦点、遮挡和有限曝光。第二批仍失败时项目进入 `backend_realism_blocked`；不得用更强调色、烟雾、颗粒或镜头词继续试图遮盖。

先按 [quality-evidence.md](quality-evidence.md) 推导项目质量 Profile 和有限 `dynamic_range_contract`，再按 [cinematic-grammar.md](cinematic-grammar.md) 从剧本推导原创 Treatment，把影视参考译成可观察行为。随后把捕获/工作/交付画幅、裁切、安全区、squeeze/desqueeze 与重构规则放入 Foundation 门。每张资产还要依据自身光线和反差继承/细化 `dynamic_range_plan`，明确曝光保护对象和允许的高光/阴影损失。格式或动态范围合同未合格，Look Test 不开始。

三套 Look 固定同一剧情事实、环境与格式，但至少在摄影机存在、光学/机位、运动、光线、环境、时间或画幅中的三类实质不同。每套按关键资产候选预算后台生成，先分别过全部硬门，再在 Foundation 中盲选唯一 Base。

## 7. Photoboard、姿态与关键帧

每张绑定：统一身份检查板、当前人物状态、地点状态视图、主锚点/道具状态、空间地图、环境、格式、批准 Profile。Storyboard 默认是照片级、可在真实位置重建的 Photoboard。

高风险手部/接触/承重动作先做 `pose_contact_anchor`。序列首尾帧优先；下一组可补充引用上一尾帧，但根和当前状态始终在前。

## 8. 镜头、路径与时间

每镜保存完整制作事实与压缩模型提示。Camera plan 保存起止 mark、坐标/朝向、primitive、承托、距离/角度、速度曲线、净空、视差、焦点和落稳。每镜动态范围计划保存有限工作宽容度、场景反差、中间调锚点、曝光优先级、亮暗行为和允许损失；禁止局部 tone mapping 与多曝光 HDR。时间记录拍摄/交付 fps、播放倍率、快门、曝光时间和速度映射；模糊记录来源、方向、区域、强度与静止参照。详见 [camera-motion-temporal.md](camera-motion-temporal.md)。

## 9. 序列与联合锚点

相邻镜头只有在人物/地点/道具/环境/特殊光/Profile/格式/时间签名完全一致时才能同组。变化即开新组，并写边界原因。每组生成联合视觉锚点，固定根引用顺序与栈哈希；逐组比较人物比例/角色体态、状态、地点拓扑、材质、天气、光线、首尾动作与模糊方向，然后只向用户发起一次序列审批。

## 10. 后台候选、门级审批与导出

生成成功不等于生产通过。身份板是一次性整板门：失败即停止人物。其他关键资产首批三张、普通资产首批两张；Codex 看实际像素并写全部相关 QA，只把通过者提升为 `qualified`。首批全失败时只改一个变量再生成两张；第二批全失败即 `model_blocked`。详见 [candidate-selection.md](candidate-selection.md)。不能用后期清理掩盖。

```bash
python3 scripts/film_project.py validate <project> --json
python3 scripts/film_project.py compile-prompts <project> --gate <gate-id>
python3 scripts/film_project.py build-review-board <project> --gate <gate-id>
python3 scripts/film_project.py record-review <project> --gate <gate-id> --decision approved
python3 scripts/film_project.py export-higgsfield <project>
python3 <project>/exports/higgsfield/verify_package.py
```

导出不访问平台。目标适配器不支持参考量、画幅或运镜段数时阻断。用户交回视频后在 start/25%/50%/75%/end 和事件帧人工审计，再决定 take 是否 selected。

## 交付

原有交付物不变。离线 Higgsfield 包额外携带 `method-routing.json`、`soul-id-prep.json`、`product-photoshoot-prep.json` 与 `audio-work-orders.json`；所有平台执行字段均为 `false`。

列出项目/导出绝对路径、Foundation/Sequence 决定、候选通过率、批准/阻断资产、身份包/角色身材/状态、地点世界/状态、环境、格式、序列/镜头数、所有 QA 与校验结果、`pixel_reproducible:false`，以及明确未执行的登录、上传和平台生成。
