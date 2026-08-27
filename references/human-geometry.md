# v1.6 人体几何与身份比例系统

本页把“像同一个真人”拆成可审计的骨架、比例、投影、承重与接触事实；角色需要什么体态另由 [role-physique.md](role-physique.md) 定义。MediaPipe Pose 的人体地标与 SMPL-X 的身体/手/脸拓扑只用于设计检查维度；本 Skill 不安装模型、不运行自动姿态评分，也不把研究许可证转成项目依赖。

## 单张统一身份板与七个确定性视图

每个持续人物恰好一个 `character_identity_inspector`。它由一次 ImageGen 调用生成一张完整 4×2 纯白底板，让所有角度共享同一次身份与身体解算：

1. 上排第 1 格 `full_front`：全身正面，也是 `body_anchor_asset_id` 的裁图来源。
2. 上排第 2 格 `full_left_profile`：全身左侧面。
3. 上排第 3 格 `full_right_profile`：全身右侧面。
4. 上排第 4 格 `full_back`：全身背面。
5. 下排第 1 格 `portrait_front`：正面脸部近景，也是 `face_anchor_asset_id` 的裁图来源。
6. 下排第 2 格 `portrait_left_profile`：脸部左侧面。
7. 下排第 3 格 `portrait_right_profile`：脸部右侧面。
8. 下排第 4 格保持纯白空白。

整板必须是同一人物、同一体态、同一身高印象、同一服装鞋履、同一自然干燥皮肤和同一中性软光。四张全身格脚底完整、站姿中性、尺度/对齐一致；水平机位与长工作距离防止广角拉伸或低机位伪造腿长。板内禁止文字、标签、边框、道具、环境、情绪布光、剧情调色或不同格各自美化。

整板先在 thumbnail、fit、100%、200% 检查身份、比例、解剖、皮肤/材质和纹理。任一格漂移即整板失败，该人物直接 `model_blocked`；不再生成第二张同身份板，不抽取“看起来还行”的局部，不生成状态或叙事帧。

通过后，`build-reference-board` 按固定网格无重采样裁出七张 PNG。裁图拥有独立 ID、裁框、源/输出 SHA-256，仅用于检查和平台 UI 若要求的分视图上传。统一板是第一且唯一的身份权威；裁图不是七次新身份解算，也不能作为状态或叙事图的根。

## Proportion signature

比例以人物自己的中性站立高度归一化为 `standing_height_1.0`，不套用统一“八头身”。若剧本要求修长、健美、模特或舞者体态，目标范围来自角色身材 Brief，并必须由统一板四张全身格共同满足；不得只靠低机位或广角制造“好比例”。全身正面和背面裁图是测量来源；左右侧面验证体积、轮廓和深度，不把透视缩短误判为比例漂移。

必须记录：

- 头高、肩宽、胯宽、躯干长度。
- 上下臂、大腿、小腿、臂展。
- 手长、足长。
- 骨性不对称、相对身高、惯用手。
- 双手/双足预期指趾拓扑。
- 每项来源、投影类别、可信度和允许误差。

比率统一除以站立高度。允许误差要反映图片分辨率与服装遮挡，不能为追求“精确”而伪造厘米值；Schema 允许每个归一化字段 0–0.15 的容差。比例签名与 `physique_fit_qa` 都通过后，身份包才可进入 Foundation 审批。

## Skeleton lock 与 soft tissue

`skeletal_lock` 冻结：头颅/肩带/骨盆关系、脊柱比例、肢段长度、关节拓扑、相对身高与预期指趾数。服装、年龄、体重、怀孕、肌肉、肿胀等不能偷偷重写骨架。

年龄、体重、怀孕、肿胀或肌肉变化进入 `soft_tissue_delta`：

- `kind` 与可见范围。
- 剧情/时间原因。
- 首次可见镜头。
- `preserve_skeleton:true`。
- 哪些面部与身体结构必须保留。

每个状态直接引用统一身份板；禁止把裁图、前一状态或叙事帧当身份根，也禁止状态到状态编辑链。

## Geometry QA

每张人物图固定检查：

- `silhouette_and_volume`：轮廓、胸廓、骨盆和四肢体积可成立。
- `joint_topology`：颈、肩、肘、腕、髋、膝、踝连接正确。
- `segment_lengths`：肢段与批准比例签名一致。
- `hands_feet_and_digits`：可见时数量、连接、长度和关节合理。
- `shoulder_pelvis_alignment`：姿态可解释，不是熔化或扭转。
- `weight_bearing_and_center_of_mass`：承重脚、支撑面和重心相容。
- `foreshortening_and_projection`：缩短来自当前视角，不是身体漂移。
- `occlusion_logic`：肢体前后遮挡顺序正确。
- `garment_body_separation`：衣物有独立结构，不与皮肤熔合。
- `multi_person_relative_scale`：多人身高与空间距离共同成立。

检查同时在缩略图、适配窗口、100% 与 200% 进行。远景中不可见的手指标记为不可判读，而不是臆造通过；关键手部镜头必须提高画面占比或另建锚点。

## Pose/contact anchor

手部接触、持械、拥抱、奔跑、跌倒、打斗、车辆上下车等高风险镜头要有独立 `pose_contact_anchor`，并以相关人物统一身份板为第一身份参考，再绑定当前状态。记录：

- 动作起点、接触瞬间与终点。
- 每个接触点的解剖侧、物体表面和力方向。
- 承重脚、重心转移、关节活动范围。
- 谁在前景/中景/后景及遮挡次序。
- 关键手指是否必须可辨、所需最小画面占比。
- 道具尺寸、握点与接地/碰撞点。

姿态锚点不替代身份根或空间地图。若动作镜头缺锚点，或锚点本身几何/接触失败，镜头不得 ready。

## 左右侧投影

关键身体侧同时保存三层事实：

- 解剖侧：人物自己的 left/right。
- 场地关系：相对固定锚点和朝向。
- 观看者投影：该机位首尾画面中的 left/right/center/occluded。

反打或转身时屏幕左右会翻转，解剖侧不会。提示和清单必须保留三层，最终以像素检查为准。

## 硬失败

额外肢体/指趾、关节断裂、肢段忽长忽短、头身比漂移、脚不接地、承重矛盾、多人相对身高无因改变、衣物和身体熔合、关键接触点穿插或错侧，全部是硬失败。角色要求的修长/健美/模特/舞者/力量轮廓被生成成短腿、塌腰、箱型躯干、错误肩腰胯或被衣服无因吞没，同样硬失败。不得用裁切、模糊或“运动中看不清”掩盖。

## 研究边界

- [MediaPipe Pose](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose.md)：用于关节/左右侧检查词汇，不作为本 Skill 的运行依赖。
- [SMPL-X](https://github.com/vchoutas/smplx)：用于身体、手和脸统一拓扑的概念参考；不安装权重，不转授许可证。
- [Higgsfield Hands & Faces](https://higgsfield.ai/blog/ai-video-hands-faces) 与 [Realistic Human Movement](https://higgsfield.ai/blog/realistic-ai-human-movement)：可迁移的是明确身份参考、可见起止状态、动作因果和足够画面占比；平台营销效果不是内置 ImageGen 的保证。
