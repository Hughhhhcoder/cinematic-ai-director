# Higgsfield 研究基线与可迁移结论

本文件只保存会改变制作决策的结论。公开项目的完整提示和媒体不进入 Skill。完整 URL 快照见 [higgsfield-public-index.md](higgsfield-public-index.md)。

## 快照与方法

- 主站索引快照：**2026-08-25（Asia/Shanghai）**；v1.5 人体/运镜/环境补充核查：**2026-08-26**；v1.6 本地质量证据、Cinema Studio 4/Seedance 2.5 官方适配与工作流更新：**2026-08-27**。
- [Higgsfield sitemap index](https://higgsfield.ai/sitemap.xml) 当日包含 8 个子 sitemap、970 个唯一 URL：marketing 144、projects 28、blog 309、Creator Hub 87、apps 100、motion 229、mixed-media presets 33、original series 40。
- 28 个 sitemap 项目均在快照时公开显示 prompts/canvas。项目页面的 generation 数从 8 到 473,214，证明逐条读取全部重复生成既不现实也会造成样本偏差；全站索引用于覆盖，深读按真人资产职能和失败类型分层，遇到重复提示与结论饱和后停止。
- 证据等级：`A` 直接公开提示—输出/参数对照；`B` 第一方帮助中心、官方模型文档和产品行为；`C` 第一方流程/教程或作者维护的开源实现；`D` 营销或推荐陈述；`E` 本 Skill 的内置 ImageGen 实测；`U` 用户提供的合法质量证据或明确制作方向。D 不能单独制定规则，开源方法也不能未经本地复测就当成内置 ImageGen 控制；U 只约束当前制作目标，不伪装成平台官方规则。
- 研究记录区分：`portable` 跨模型原则、`higgsfield-specific` 平台控制、`imagegen-calibrated` 本地重复测试。

## v1.6 本地质量证据与适用边界

2026-08-27 的用户提供照片被作为 `U` 级质量证据审查。可迁移内容是：可解释的柔和光源、皮肤高光随面部曲面连续变化、自然肤色与中间调、头发/针织物/木/墙面互不共享纹理、生活化布景因果、普通人物的任务式表演和非宣传式构图。它支持 `clean-observational-live-action-v001` 质量底线。

不可迁移内容包括该人物身份、年龄、住宅、服装、日间光线、焦段、构图和观察式题材本身。原图不打包、不进入 ImageGen 生产引用；每个项目必须从剧本重新推导 `project_quality_profile`。因此“质量像这张照片”不是“所有作品都生成成这张照片的风格”。

角色身材匹配是用户明确的制作方向（U），不是 Higgsfield 官方固定分类。Skill 将其翻译为 `role_physique_brief + proportion_signature + physique_fit_qa`：普通、修长、健美、强壮、模特、舞者、耐力或剧情特定体态都由角色事实决定；目标驱动分类必须有可测范围和候选淘汰条件。这个系统能阻断不符合体态的结果，但不宣称模型首次生成必然命中。

v1.6 的后台候选与低打扰审批采纳了公开项目可观察到的“多次生成和筛选是品质组成部分”，但候选数量、Foundation/Sequence 门和失败隐藏策略是本 Skill 的原创生产规范，不应误称为 Higgsfield 固定产品流程。

有限动态范围规则来自跨模型的物理摄影证据，不冒充 Higgsfield 专属按钮：[ARRI Dynamic Range White Paper](https://www.arri.com/resource/blob/295460/e10ff8a5b3abf26c33f8754379b57442/2022-09-28-arri-dynamic-range-whitepaper-data.pdf) 明确说明场景反差超过摄影机动态范围时必须在高光与阴影之间取舍，降低曝光可多保高光但会少保阴影；[Sony VENICE 2](https://pro.sony/en_GB/products/digital-cinema-cameras/venice2) 以 18% 灰上下有限 stops 描述 latitude；[Kodak VISION3 500T](https://www.kodak.com/content/pdfs/motion/KODAK-VISION3-500T-5219-7219-brochure.pdf) 与 [VISION3 250D](https://www.kodak.com/en/motion/product/camera-films/250d-5207-7207/features/) 也只支持宽容而非无限记录。Skill 因此要求每张图/每镜声明曝光优先级与允许损失，禁止“每个亮暗都完全看清”的生成式伪 HDR；生成图只模拟行为，不声称真实机身、胶片或 EXIF。

## 当前公开项目目录

按 generation 数降序：Cully Hill Boys、HELL GRIND、ONEIRIC、ZEPHYR、4K Blockbuster Breakdown、Kok Boru film、Adiliada、ZEPHYR: Special、If You Stop Loving Me...、Red Flag、Kok Boru carousel、Ultra Realistic AI Short Film Breakdown、Cat Story、Seed Audio 1.0 Launch、Dusk、One More Time、Anime Production、The New Girl、Top Up、Huntress's Tale、Higgsfield Academy、Nala、Soul Carousels、REWIND CLUB、Seedance 2.0 4K Showcase、Gothic Beach、Space Chores、Office Bathing。

动画项目只参与平台方法辨析，不构成本 Skill 的题材模板或触发范围。项目列表会变化，名称和计数只描述快照。

## MUMYEONG 全量结构审计

主要个案：[무명 — MUMYEONG](https://higgsfield.ai/@farhatzayed/projects/mumyeong)。

- 项目元数据：136 generations；Seedance 2.5 为 66、Seedream 5 Lite 为 47、Seedream 4.5 为 20、Cinematic Video Editor 为 2、Flux 2 为 1。
- 公开文件夹接口在快照时返回 138 items，其中 129 条非空提示、117 条精确去重提示。元数据 generation 数和文件夹 item 数口径不同，因此不再声称固定“62 条提示”。
- 资产分布：Shots 64 items、Char 24、Loc 15、Prop 11、Key Arts 16，另有根项目/非 generation 项。
- 人物提示：24 条、17 个精确唯一版本，159–501 个英文词；经常以三联参考表锁年龄、体型、脸部不对称、皮肤风化、发型、服装和正背视图。
- 地点提示：15 条、14 个唯一版本，125–342 词；普遍要求无人、空间三维关系、具体设施/家具位置、摄影机高度和可读地理。
- Shots：62 条含提示、59 个唯一版本，中位数约 662 词；常见完整分段、角色/地点 reference elements、逐秒动作、表演、音频和 positive locks。
- 直接观察：复杂视频依赖批准参考和空间地图；人物/地点母版依赖具体个体与因果细节。`photoreal`、`fine film grain` 等词在项目中高频出现，但高频不证明它们是成功原因。
- 项目存在精确重复提示和多次生成，说明最终品质包含筛选效应；任何“一个提示必然得到该画面”的推断都不成立。

## 关键官方证据

### A/B：产品如何得到摄影差异

- [How We Built Cinema Studio](https://higgsfield.ai/blog/how-we-built-cinema-studio)：团队逐组测试相机/镜头，让在职摄影机操作员判断是否像 AI；无法复现的著名镜头被移除，镜头性格还被手动放大。结论：器材名是平台/模型经验证的控制，不是普适物理定律。
- [Cinema Studio 4.0](https://higgsfield.ai/blog/cinema-studio-4-0)：镜头、光圈、年代、调色和最多 50 个参考是产品级直接控制。把这些控制名称复制进普通 ImageGen 文本不等于拥有同一系统。
- [Soul Cinema Help](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-soul-cinema)：其“cinematic/atmospheric”是模型内置先验；这进一步证明平台输出不能只归因于提示文字。

### B/C：提示和参考的实际职责

- [AI Short Film – Full Prompt Library](https://higgsfield.ai/blog/ai-short-film-youtube-guide)：官方完整短片例给出一张两排人物 reference sheet：上排全身正面、左侧、右侧、背面，下排脸部正面、左侧、右侧和留白；地点 reference sheet 使用正面、左右 angled perspective、反向广角和细节。结论：人物多角度应共享同一张身份表的联合解算，而不是七次随机身份；地点多视角承担真实空间覆盖。Skill 严格采用该四列两排职责布局，并增加“整板先验收、记录实际白色横向 gutter、再无缩放确定性裁七图、Inspector 始终是第一权威”的可审计实现；不把官方职责顺序误写成必须数学等高的像素网格。地点 `side_three_quarter_wide` 的 30–60° 范围是对官方 `angled perspective` 的内部可验证规范，不冒充官方精确角度要求。
- [Realistic AI Human Movement](https://higgsfield.ai/blog/realistic-ai-human-movement)：Cinema Studio Cast 的 character sheet 明确包含 front/side/back；与上项构成交叉证据。
- [How to Write a Good Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt)：先做中性人物底图，明确 keep/change；有起始图后，视频提示转向动作、镜头和时序；简单任务保持简单，迭代时一次改一项，少量关键 negatives 即可。
- [Common Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes)：过量细节会竞争注意力；主体/年龄/体型/服装与空间阻挡应优先，长排除清单会稀释目标。
- [Characters and Locations](https://higgsfield.ai/blog/consistent-characters-locations)：面部和地点各需要稳定参考；文字重述不能替代同一次生成中的锚点。
- [Script to Storyboard](https://higgsfield.ai/blog/script-to-storyboard-ai)：参考收集是最常被跳过但最影响一致性的步骤；强输出应继续作为下一段参考。
- [Soul ID](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-create-and-use-a-soul-id-character)：清晰、近期、角度多样且获许可的真实照片比大量不一致照片更有效，也确认真人身份使用必须得到许可。
- [Seedance 2.5 Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)：官方模型提示顺序为 `GLOBAL STYLE → SCENE → CHARACTERS → LOCATION → FIRST FRAME AND BLOCKING → Shot n → OPTICS → CAMERA → PHYSICS → LIGHTING → AUDIO`；多镜头使用编号 Shot、明确 blocking 与 `Hard cut`。公开能力包括最长 30 秒、最高原生 1080p、最多 50 个参考、9:16–21:9 和原生音频。v1.6 将这些事实固化为带日期适配器；任一不匹配都阻断，不能用营销描述替代界面核对。
- [AI Video from a Script](https://higgsfield.ai/blog/make-ai-video-from-script)：官方当前脚本工作流是剧本格式化、拆场、建 shot list、逐镜生成和组接；整份剧本一次粘贴会得到泛化单镜。Cinema Studio 可预填镜头参数，但正式生成前仍需人工复核。
- [Cinema Studio 3.0](https://higgsfield.ai/blog/cinema-studio-3)：公开步骤是先上传人物/地点参考，再描述故事、配置镜头和生成；参考图数量属于平台版本行为，不应固化为跨版本 Schema。
- [Camera Control](https://higgsfield.ai/blog/ai-video-camera-control)：可执行控制来自明确的运动类型、速度/路径、镜头与起止构图；“dynamic cinematic camera”一类形容词不能替代这些事实。具体可用控制仍属于 Higgsfield 版本行为。
- [Hands & Faces](https://higgsfield.ai/blog/ai-video-hands-faces)：手与脸需要明确身份参考、动作起止、可见接触和足够画面占比；这支持 v1.5 的 pose/contact anchor 与关键手部占画门，而不是证明文字提示必然修复解剖。
- [Realistic Human Movement](https://higgsfield.ai/blog/realistic-ai-human-movement)：动作应拆成有因果的离散节拍，并明确重量转移、接触和状态对比；营销效果不能替代逐帧几何/物理检查。
- [Seedance Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide)：镜头数、时长、画幅和分段动作应显式声明；该结构可迁移，具体段数与能力必须留在版本化适配器。

### B/C：人体、体积、时间与物理 QA

- [MediaPipe Pose](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose.md)：33 个身体地标提供左右侧、关节拓扑和承重审计词汇；本 Skill 不安装、运行或冒充其自动测量。
- [SMPL-X](https://github.com/vchoutas/smplx)：统一身体、手和脸的拓扑支持把身份骨架与软组织状态分开描述；其代码/模型和许可证不成为 Skill 依赖。
- [VBench](https://github.com/Vchitect/VBench)：主体/背景一致性、闪烁、运动平滑、人类动作和空间关系等维度可转成人工 take QA；不运行其模型、不报告虚构分数。
- [PhyGenBench](https://github.com/OpenGVLab/PhyGenBench)：物理现象是否出现、事件顺序与整体自然度可转成人工物理审计；不把其评分器当本 Skill 的自动验证器。
- [PBRT Volume Scattering](https://pbr-book.org/3ed-2018/Volume_Scattering) 与 [ASC Shot Craft: Smoke and Fog](https://theasc.com/articles/shot-craft-smoke-and-fog)：雾烟需要距离相关吸收/散射和可解释光源角度，支持环境状态中的能见度、衰减与光束因果；不能据此声称生成器会自动求解物理。

### C/D：真实感与失败解释

- [Make AI Video Look Real](https://higgsfield.ai/blog/ai-video-look-real-2026)：可识别光源、重量转移和人类摄影机行为比 `realistic/cinematic` 更可执行；同一修正必须在具体模型/场景中对照生成。
- [AI Short Film Pipeline](https://higgsfield.ai/blog/ai-short-film-pipeline)：角色、地点、分镜、摄影控制、音频和剪辑是一个依赖系统；该文章同时推销平台集成，流程形状可迁移，产品效果声明不可直接迁移。
- [AI Documentary](https://higgsfield.ai/blog/ai-documentary-videos-2026)：年代和真实事件需要可靠资料与持续引用；重演必须标记资料边界。
- [Why Generations Fail](https://higgsfield.ai/blog/why-ai-video-generations-fail)：更明确参考和动作常能减少猜测，但“所有失败都只是描述不足”是厂商化简，不能排除模型能力边界。

### B/C：跨次身份与序列研究

- [OpenAI Image Generation](https://developers.openai.com/api/docs/guides/image-generation)：官方明确说明跨多次生成保持重复人物或品牌元素仍可能困难；同时 GPT Image 支持多个高保真图像输入。结论：多参考是可用手段，但审批淘汰仍是必要生产门，不能承诺逐像素或首次生成一致。
- [PhotoMaker](https://github.com/TencentARC/PhotoMaker)：作者实现用排序后的多张身份照片共同约束身份，并建议增加同一人的有效照片以提高身份保真。可迁移的是“多视角身份库优于单张漂亮肖像”，不是其模型权重或参数。
- [StoryMaker](https://github.com/RedAIGC/StoryMaker)：作者目标同时覆盖面部、服装、发型和身体的长程一致。可迁移的是把整体身份与持续服装状态共同审计，而非只比较脸。
- [StoryDiffusion](https://github.com/HVision-NKU/StoryDiffusion)：作者以序列级一致注意力处理长程故事图像。可迁移的是先按持续状态形成序列组、比较组内首尾和再次登场帧；内置 ImageGen 不具备该仓库的专用机制，因此仍需根参考和人工门。
- [GPT Image 2 Artifact Cleaner](https://github.com/Larryvrh/gpt-image-2-artifact-cleaner) 记录了过锐、随机亮点、不自然边缘和鳞片状纹理等可观察问题，也说明强清理会损失真实细节且结果非像素精确；其 [PolyForm Noncommercial 许可证](https://github.com/Larryvrh/gpt-image-2-artifact-cleaner/blob/main/LICENSE) 不符合本 Skill 的通用商业复现边界。Skill 只把这些症状纳入 QA，不安装、调用或分发该工具。

## 跨案例可迁移结论

1. **参考优先于重述**：身份、地点、关键物件和强上一帧应成为职责明确的参考；参考数量服从任务，不追求上限。
2. **母版先于情绪 Look**：中性人物和地点先解决“是谁/在哪里”，叙事图再解决“怎样看”。
3. **复杂度按任务分配**：人物/地点静态提示不应复制多镜视频的巨大分段；完整制作记录和模型提示必须分离。
4. **空间先于动作**：场景状态多视角、唯一固定锚点、摄影机/人物标记、通路、接触点和画面数量明确后，动作和摄影才有可执行基础。
5. **选择是流程的一部分**：重复生成与失败不可从公开成片中消失；Skill 必须记录尝试、拒绝和停止条件。
6. **相机名不是摄影**：品牌只有在目标 ImageGen 的重复实测中产生稳定可见结果才进入提示；摄影清单仍以行为和叙事为权威。
7. **真实不等于统一粗糙**：观察式对白、夜景动作、年代纪录和精密广告需要不同 polish ceiling；通用浅景深、青橙、逆光和颗粒会制造新的 AI 模板。
8. **身份需要转面证据**：重复角色不能只靠一张正面漂亮肖像；正、侧、背和脸部近景共同约束骨骼、体型、服装和发型。
9. **每个场景状态需要两个基础空间证据**：建立图说明整体，侧面三分之四图说明相邻平面与纵深；两者共享一个稳定、尺度可读的主锚点。多轴场景再补正面、左右三分之四和反向证据，不能让模型用“相似房间”补全。
10. **屏幕方向不能代替场地关系**：反打会交换画面左右；人物、摄影机、锚点和移动路径必须同时保存不随镜头翻转的固定坐标与自然语言地标关系。
11. **平台适配必须与制作事实分层**：Higgsfield 的 UI、模型和参考预算会变；便携包应固定批准资产、句柄、逐镜空间地图、提示和完整摄影事实，并在运行时映射到当前界面，而不是把易变按钮写成故事权威。
12. **根身份与状态必须分离**：一次生成的高分辨率 3×2 白底 Inspector 是新项目唯一第一身份根；六张无缩放裁图只是检查/UI 文件。旧 4×2 只保留兼容适配。服装、湿润、伤势和软组织变化只能记录相对 Inspector 的增量，并始终把它放在引用栈首位，禁止状态递归、角度递归或失败格向下传播。
13. **世界拓扑与地点状态必须分离**：固定墙门窗、设施、尺度和锚点属于 `location_world`；昼夜、陈设、天气和损坏属于可追溯的 `location_state`，离开后返回仍引用同一个 world。
14. **连续性应按序列验证**：相同人物/地点/道具状态、灯光和摄影 Profile 聚合为 sequence；状态变化开启新组，上一尾帧可以桥接，但不能替代身份和地点根。
15. **微小增量必须可验收**：模型若连续两次把局部缺陷扩大、错位或扩散，就应 `model_blocked`，不能接受“剧情意思接近”。必要时制作局部近景权威或请求合法实拍参考。
16. **左右侧是三层事实**：解剖左/右是身份事实，场地固定关系是世界事实，画面左/右是当前机位的投影。关键持物、伤势与包扎必须同时记录并逐图检查。
17. **可复现的是工作流，不是像素**：提示、引用顺序、哈希、状态锁、审批与导出可跨电脑复现；随机生成结果不能被虚构为相同像素。
18. **人体按本人比例，不按理想模板**：正背面提供归一化比例证据，侧面/三分之四验证体积；透视缩短、姿态和软组织变化必须与骨架漂移分开。
19. **环境是物理状态，不是氛围滤镜**：天气、雾烟和特殊光必须有来源、方向、距离衰减、材料/人物后果与时间边界。
20. **运动需要空间和时间双重重建**：pan/tilt、位移与 zoom 必须区分；路径、承托、快门、播放倍率和模糊方向共同决定是否像真实摄影机。
21. **影视参考必须翻译**：片名、导演、机身或胶片只能触发内部分析；模型提示只保留原创、可观察、可验证的摄影行为。
22. **皮肤高光是光路证据，不是电影滤镜**：必须能从真实光源的大小、方向、人物干湿状态与曲面朝向解释；均匀油膜、孤立亮斑、只染皮肤的青橙边光和 HDR/clarity 雕刻都是游戏过场式失败。
23. **负面对照不属于候选**：历史坏提示与已存在失败图可用于研究，但不得重新生成或展示为盲选项。用户只审批已经逐张通过实拍、纹理、几何与光材硬门的正向候选。
24. **质量证据不等于风格复制**：优秀实拍照片可以定义高光、肤色、材质、焦点和表演的最低标准，但人物、住宅、日夜、构图和题材不得泄漏到新项目。
25. **“好身材”必须翻译成角色目标**：修长、健美、模特、舞者、力量或耐力体态需要各自可测范围、轮廓事实和候选淘汰条件；既不能统一套八头身，也不能以“普通真实”为由接受不符合选角的差比例。
26. **低打扰来自后台淘汰，不是放宽门槛**：用户按 Foundation 与序列审批；逐图四尺度检查、候选失败记录和直接依赖返工仍在后台完成。
27. **官方符合必须版本化**：Higgsfield 的严格保证只指明示 Profile 下的提示顺序、参考职责、上限和文件合同；若当前官方界面与 `2026-08-27` 快照不一致就阻断并更新，不能声称控制第三方随机像素，也不能静默降级。
28. **动态范围必须做取舍**：真实摄影的工作宽容度有限；每张资产和镜头必须写场景反差、曝光优先级、中间调锚点、亮部/暗部行为及允许损失。若场景反差超出工作范围却声称高光暗部全部完整，或使用局部 tone mapping/多曝光 HDR 把所有区域同等提清，必须失败。

## 本地 ImageGen 校准状态

2026-08-26 已用内置 ImageGen 完成 v1.4 两层实测。第一层为人物、混合材质地点、道具、叙事画面四类 × v1.3 旧提示、v1.4 干净事实版、v1.4 干净参考驱动版三条件 × 两次独立生成，共 24 张；第二层为同一虚构人物跨三个地点、四个持续状态和八个保留叙事帧，以及同一地点日/夜、重新布置、受损和返回。结果见 [imagegen-calibration.md](imagegen-calibration.md) 和基准项目 `ai-film/cinematic-director-v1-4-benchmark/qa/`。

- 旧式通用脏化词在四类样本中稳定传播为全局粗粝、美化或跨材质的统一质感，标记 `drop`。
- 干净事实版和干净参考驱动版在每类的两次重复中都通过四尺度纹理硬门；纯文本只可建立候选，参考驱动版才进入一致性生产链，且仍需逐图 QA。
- 八张保留叙事帧没有纹理硬失败；人物在三个地点的可见身份不变量、地点固定拓扑和声明状态保持到内部基准门槛。
- 两个微小右袖撕口候选都把 2 cm 缺陷放大，已 `model_blocked`；两个右手持板候选都镜像到左手，也已阻断。失败没有进入后续参考。
- 左手绷带第一次镜像，第二次加入解剖侧与当前机位观看者投影后纠正；因此该写法是 `conditional` 提示规则，不是保证。
- 基准证据只批准提示/QA 规则进入 Skill；其中任何图都没有被冒充为用户生产批准资产。

未经重复测试的器材、导演和胶片名继续默认 `drop`。不能把 Higgsfield 或开源模型结果冒充内置 ImageGen 结果；`pixel_reproducible` 保持 `false`。

## v1.5 校准发布状态（历史，已被 v1.6 单板身份规则取代）

v1.5 曾实现七图身份联络表、人体/环境/格式/路径/时间/动态模糊阻断规则和 Higgsfield 映射。其“七图分别生图”方式因身份漂移在 v1.6 被废止，不能用于新项目。其余历史实证只用于解释旧版本，不覆盖 v1.6 的单板身份与官方适配发布门。

- 所有 `medium_signature` 默认 disabled，不得自动加入提示。
- 生产叙事图回退 `clean_narrative` 洁净数字成像。
- 新天气、微距、高反/透明、水下、高速运动或多人接触继续逐资产审查，不能用 v1.4 结果冒充 v1.5 通过。
- 单元测试通过只证明清单和阻断逻辑，不能证明具体像素已经没有 AI 伪影。
