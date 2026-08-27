# 人物身份包与状态系统 v1.6

人体比例、统一 Inspector/七张确定性裁图和姿态接触的详细门槛见 [human-geometry.md](human-geometry.md)，角色匹配体态见 [role-physique.md](role-physique.md)。本页只定义身份、持续状态与逐镜表演之间的边界。

## 单张身份权威

每个持续人物恰好一个 `identity_pack` 和一个 `character_identity_inspector`。Inspector 是一次 ImageGen 调用生成的 4×2 纯白底板：上排 `full_front / full_left_profile / full_right_profile / full_back`，下排 `portrait_front / portrait_left_profile / portrait_right_profile / blank`。

- Inspector 整板是第一且唯一的身份权威；全部七个有效格必须共享同一人物、体态、服装、尺度、皮肤状态和中性光。
- `face_anchor_asset_id` 等于从 `portrait_front` 格确定性裁出的检查文件；`body_anchor_asset_id` 等于从 `full_front` 格确定性裁出的检查文件。两者是 alias/上传便利，不是新身份根。
- 整板只生成一次。任何格出现身份、角色体态、解剖或洁净实拍质量漂移，立即停止该人物并 `model_blocked`；不从坏板裁图，不重试同一身份。
- 通过后由 `build-reference-board` 检测并记录中心白色横向 gutter 的实际 row split，再无重采样裁出七张检查/上传 PNG；分隔歧义、内容跨界或裁掉头发/鞋履直接失败。裁图只能直接派生自 Inspector，不能再次生成或递归编辑。

## Immutable identity

冻结：

- facial bone proportions
- feature spacing
- body build and height ratio
- skin-tone range
- hairline
- fixed marks
- handedness
- approved `proportion_signature` 与 `skeletal_lock`
- approved `role_physique_brief` 的未声明体态字段

状态增量不得包含上述字段。视角变化、姿态、焦段或透视造成的投影差异需要被解释，但不能登记为新身份。

## Persistent state

持续状态包括服装、发型状态、年龄阶段、伤势、湿润、局部污损、妆容和剧情道具。基线也显式登记，例如：

```json
{
  "wardrobe": "plain navy cotton work shirt, charcoal trousers",
  "hair_state": "dry, tied low",
  "age_stage": "adult baseline",
  "injury": "none",
  "wetness": "none",
  "dirt": "none",
  "makeup": "none",
  "story_props": "none"
}
```

每个 `character_state`：

- 直接引用统一身份 Inspector 作为第一身份输入，顺序固定。
- 独立生成一张中性状态参考，不使用另一状态或桥接帧做输入。
- `state_delta` 只写相对根身份的持续变化。
- `soft_tissue_delta` 只管理年龄、体重、怀孕、肌肉、肿胀等软组织改变，必须有成因、起始镜头并 `preserve_skeleton:true`。
- 全部 immutable 与 proportion signature 逐项保留。
- `preserve_role_physique:true`；服装状态不得把批准肩腰胯、腿/躯干或力量/舞者轮廓改成另一体型。
- 通过身份、角色身材、几何、摄影和 `live_action_quality_qa` 后进入对应审批门。

## Transient performance

情绪、视线、嘴型、呼吸、手势和单镜动作是逐镜表演，不创建新身份状态。只有跨镜持续、剪辑后仍可见的改变才进入 state。高风险接触动作使用 `pose_contact_anchor`，但姿态锚点也不是人物状态。

## 左右侧与关键手部

`handedness` 是身份事实，伤势/绷带/持物侧是状态或镜头事实。三层同时保存：

1. `anatomical_side:left|right`。
2. 相对主空间锚点和人物朝向的场地关系。
3. 当前机位的 `viewer_projection:left|right|center|occluded`。

转身或反打会改变第三层，前两层不变。提示可以写 `her anatomical left hand, appearing on the viewer's right in this frontal view`，但最终以图像/视频 QA 为准。

## 微小局部状态

`localized_story_evidence` 必须登记材质、解剖/物件部位、范围、成因、首次镜头和最小可验证画面。若全身或中景无法确认 2 cm 级损伤，先制作局部中性近景权威。连续两次扩大、错位、镜像、复制或跨材质扩散即 `model_blocked`，不能用近似或后期涂抹通过。

## 跨场景审计

在每个 sequence 首帧、尾帧和再次登场帧并排检查：

- 面部骨骼、五官间距、发际线、固定标记。
- 头身、肩胯、肢段、手足和多人相对身高。
- `role_physique_brief` 的 must-have、量化目标、姿态/步态与 wardrobe silhouette。
- 当前状态服装结构、软组织变化、伤势/湿润边界。
- 惯用手、关键身体侧、持物与接触点。
- 未声明字段是否漂移。

任何漂移不得进入 qualified/approved。两批无法稳定时标记 `model_blocked`，请求用户提供有权使用且获真人同意的多角度实拍参考。

## 真人与虚构人物导出

- `identity_kind:real_person`：输出 Soul ID 准备清单；上传前再次确认权利与同意。
- `identity_kind:fictional`：输出 Elements/Soul Cast 准备包。
- 两者都以单张统一身份 Inspector 为 ground truth；七张裁图仅为检查/UI 上传便利，当前状态单独绑定。
