# 融合官方三项 Skill 的方法，但不操作平台

v1.7 学习官方 `higgsfield-generate`、`higgsfield-soul-id` 和
`higgsfield-product-photoshoot` 的标准，同时保持原来的交付边界：仍只生成本地
资产、清单、提示、评审板、剪辑/声音计划和离线制作包；不安装 CLI、不登录、
不上传、不训练、不提交生成、不轮询，也不消费积分。

## 真正吸收的内容

- 先按任务意图区分图片、视频、音频、分析、商业视频和商品摄影，再写提示。
- 每个参考文件只承担一个明确职责，并保持确定性顺序。
- 模型提示只保留会影响画面的事实；QA、权利、哈希和重建信息留在 JSON。
- Soul 素材的数量、清晰度、多样性、使用权和真人同意标准。
- 商品事实锁和十类按用途选择的商品摄影模式。
- 与画面节奏、剪辑和混音职责绑定的独立音频工作单。

## 明确不模拟的能力

Soul 训练和平台 reference ID 仍是平台专属能力；Product Photoshoot 的后端
提示增强也仍是平台专属能力。制作包只输出商品事实与简短意图，绝不伪造或暴露
后端增强后的 GPT Image 2 提示。

模型名称只是带日期的建议。未来由人类使用制作包时仍需核对当前 Schema；不能因为
版本号更大，就假设参考数量、时长、分辨率、音频和编辑行为全面升级。

## 身份职责必须分开

项目里的单次身份解算 `3×2` Inspector 仍是电影连续性的第一身份权威。真人 Soul
就绪度是另一件事：需要 5–20 张独立、合法、获得同意的用户照片，8–12 张为理想
范围；每张只有一个人、眼睛清晰、对焦准确，并覆盖不同角度、光线、表情和距离。
生成的 Inspector 绝不能计入这组真人照片。

## 商品事实和模式

任何广告衍生之前，先锁定商品几何、标签文字、Logo 位置、颜色、材质、比例、活动
部件、必须保留细节和允许的状态变化，再按真实用途选择一个模式：
`product_shot`、`lifestyle_scene`、`closeup_product_with_person`、
`moodboard_pin`、`hero_banner`、`social_carousel`、`ad_creative_pack`、
`virtual_model_tryout`、`conceptual_product` 或 `restyle`。

## 原制作包新增的本地文件

- `manifests/higgsfield-methods.json`：证据、路由和准备事实。
- `method-routing.json`：任务族、参考职责、提示预算和日期化能力建议。
- `soul-id-prep.json`：真人照片就绪度，不训练。
- `product-photoshoot-prep.json`：商品事实和简短意图，不含伪造增强提示。
- `audio-work-orders.json`：逐镜声音和节奏职责。

所有平台执行字段都固定为 `false` 并由验证器检查。
