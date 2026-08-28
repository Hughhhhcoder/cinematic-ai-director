# v1.6 连续性与生产硬门

连续性不是“看起来差不多”，而是每个批准镜头都能追溯到同一组身份、比例、世界、状态、空间、环境、格式、摄影和时间事实。

## 静态资产 QA 层

### Photographic QA

机位、有效画幅、镜头/FOV、焦点、曝光、真实光源、材质响应和 Profile 可近似重建。

### Geometry QA

轮廓/体积、关节拓扑、肢段、手足/指趾、肩胯、承重/重心、透视缩短、遮挡、衣物/身体分离和多人相对身高。

### Live-action quality QA

无动画、插画、CG/PBR、游戏过场、蜡/塑料皮肤、假体眼、毛发粘块、织物熔化、渲染描边、补丁涂抹、重复/跨材质伪纹理。人物另逐项通过：

- 皮肤高光尺寸、方向和范围符合声明主光及干湿状态。
- 肤色、阴影与彩光在面部曲面和邻近物体间连续传播，不出现独立油膜或双边美容光。
- 局部对比/色调映射不过度雕刻皱纹、眼窝、鼻唇沟、头发或轮廓。
- 皮肤、毛发、服装、墙面、金属和釉面粗糙度相互独立。
- 人物动作由任务、承重和空间阻挡产生，不是英雄伸手、海报凝视或游戏预告片姿态。
- 多人物镜头记录批准身高、人物—摄影机距离、预期/观察投影比、地平线和共同或明确高差的接地面；不能为构图单独缩放某个人物。

### Spatial/environment QA

地点视角、相邻平面、拓扑、锚点位置/比例/方向、机位可达性；天气来源/方向/积累、距离衰减、材质反应、曝光/焦点、声音与时间边界。

### Dramatic coverage / subject-environment integration QA

两人以上叙事镜头必须证明：空间证据没有替代镜头覆盖；coverage role、观看者位置、景别/裁切地标、前景与焦点人物、相交视线和动作节拍均已冻结。对称全身宽景只有在 `wide_two_shot_justification` 有明确叙事理由时可用。

所有人物还必须共享同一摄影事件的光线、环境介质、焦点/模糊、遮挡、接触/支撑、材质与色彩传播、边缘锐度和色调映射。任何 cut-out 边、人物单独美容光、独立 HDR/锐化、空气只作用于背景、脚底/门槛支撑不成立或游戏关卡式站位均为硬失败。`spatial_qa=pass` 与 `multi_person_projection=pass` 不能覆盖这两项失败。

此统一门还要求十二项 `positive_evidence`、无关材质配对与四尺度检查。任何相关 QA 缺失或失败，资产不得进入 `qualified`；用户决定只存在 Foundation/Sequence 审批门。

## 身份与状态连续性

逐 sequence 首帧、尾帧和再次登场帧比较：

- 统一 4×2 身份 Inspector、七张确定性裁图与 `proportion_signature`。
- `role_physique_brief`、量化目标、姿态/步态和衣着轮廓。
- 头身、肩胯、躯干/肢段、手足、骨性不对称、相对身高。
- 面部骨骼、五官间距、发际线、固定标记和惯用手。
- 当前 wardrobe、hair、age、injury、wetness、dirt、makeup、story props。
- `soft_tissue_delta` 范围与 skeleton lock。
- 关键解剖侧、观看者投影、姿态与接触点。

未声明变化即漂移；不能把漂移注册成新状态来“修复”。

## 世界、空间与环境连续性

- 地点 topology/openings/fixed facilities/scale/material baseline/primary anchor 不变。
- state delta 的时间、陈设、损坏和环境后果有起始镜头与因果。
- 主锚点位置、方向、接地与尺度跨视角不漂。
- 摄影机/人物 mark、运动路径、depth order 和画外锚点方向一致。
- 雨雪/雾烟/尘/水下/热浪随时间连续，积累和服装/地面后果不重置。
- 闪电、火光、警灯等光事件的波形、阴影、反射和声音同步。

## 格式、摄影与运动连续性

- 镜头使用批准的 Profile、Treatment 和 format plan。
- 序列画幅覆盖有转换与 return rule，且没有烧入黑边。
- 机位、焦段/FOV、T-stop、焦点和曝光不矛盾。
- camera path 从批准 marks 出发，不穿墙、不漂浮，承托/速度/视差合理。
- capture/delivery fps、播放倍率、快门与曝光时间一致。
- 模糊来源、方向、区域与静止参照符合主体和摄影机运动。
- Medium signature 只在批准范围内；不稳定时回退 clean narrative。

## Sequence signature

相邻镜头只有以下签名完全一致才可同组：

```text
location_state_id
environmental_state_id
sorted special_lighting_event_ids
sorted character_state_ids
sorted prop_state_ids
capture_profile_id
format_plan_id
temporal_capture_signature
lighting_state
```

变化即开新组并写 `boundary_reason`。上一组尾帧可以做 supplementary bridge，但不能取代统一人物 Inspector、当前状态、地点根或锚点。

## Ready/export 阻断

以下任一项缺失都阻断：

- 批准统一 Inspector、七张确定性裁图、比例签名、精确人物/地点/道具状态。
- 批准角色身材 Brief 与 `physique_fit_qa`；镜头 body lock 同时引用比例和身材 ID。
- 批准 environment、format、Profile/Treatment 与 spatial map。
- 高风险动作所需 pose/contact anchor。
- 可重建 camera path、正确 exposure time、完整 motion blur plan。
- `live_action_quality_qa`、几何、摄影、空间/环境与 cross-scene QA。
- 含人物资产的完整 `material_response_contract`，包括光源大小/方向、皮肤干湿、高光范围、局部对比、色调映射、材质粗糙度与表演策略。
- Foundation/Sequence 门批准、合法参考来源、quality Profile、联合视觉锚点、引用栈哈希、首尾关键帧和 sequence signature。
- 两人以上镜头的 `dramatic_coverage_plan` 与所有含人物镜头的 `subject_environment_integration`；两项都必须 `verdict=pass` 且无 hard failures。
- 目标 Higgsfield 适配器对参考量、画幅或运镜段的支持。

## Take temporal QA

用户交回视频后，至少检查 start、25%、50%、75%、end，以及接触、光变、速度、焦点和剪辑事件附近：

- identity/body consistency
- background consistency
- texture crawl/flicker
- morphing/ghost limbs
- lighting/exposure continuity
- environment advection/material response
- camera-path conformance
- focus/motion blur
- rolling shutter/frame blending
- start/end-frame match

这是人工审核，不声明 VBench、PhyGenBench 或其他模型自动分数。QA 由 `codex-visual` 记录；需要用户选择时走门级决定。

## 失败与升级

第一次图像失败只允许一次独立单变量修正。人物/地点权威或洁净表面第二次仍失败：`model_blocked`，请求合法实拍参考。视频 take 失败保留记录并生成具体修订提示；不得把失败 take 当下一序列唯一桥接。
