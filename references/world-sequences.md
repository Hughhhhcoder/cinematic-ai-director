# 世界状态与跨场景序列系统 v1.6

## Production-design DNA

全项目先锁定年代、社会经济条件、建筑/设施逻辑、真实颜色来源、材料、公共设施、标识和允许的老化程度。DNA 是因果规则，不是统一调色或“电影脏感”。

## Location world 与 state

`location_world` 不变量：拓扑、门窗、固定设施、主锚点、尺度关系和材料基线。`location_state` 只允许改变时间、环境、现场灯、移动陈设和剧情损坏。

同一地点状态不变时跨场景复用同一个 ID；离开后返回仍复用。新 state 必须记录第一条可见镜头、原因、允许增量、保留项和独立状态视角。新增门窗、移动固定设施、改变尺度/锚点/材料基线均为 `LOCATION_DRIFT`。

## Environmental state 与 special light

每场显式绑定一个批准 `environmental_state_id`，包括 clear。雨雪、雾烟、尘、风暴、火焰/余烬、水下和热浪保存来源、强度、能见度、尺度、方向/风、积累、人物/材料反应、散射/衰减、焦点/曝光、声音与起止镜头。

闪电、火光、警灯、屏幕/投影等用 `special_lighting_event_ids` 保存波形、曝光、阴影、反射和主体/环境响应。完整规范见 [atmosphere-weather.md](atmosphere-weather.md)。

## Prop state

物件根锁定制造结构、尺寸、材料和多视图；状态只允许剧情增量，例如封条打开、液位下降或明确局部损伤。状态图直接引用根，未声明区域保持。主锚点若会移动就不适合作为主锚点。

## Sequence cluster

只有相邻镜头下列签名完全相同才能同组：

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

任一持续状态变化即开新组。每组必须有 `sequence_visual_anchor_asset_id`，联合当前人物状态、地点状态、主空间锚点、光线方向与 quality Profile；并保存批准首/尾关键帧。上一组尾帧可作 `bridge_frame_asset_id`，但必须与根权威同时提供。

### 分组步骤

1. 按剪辑顺序列出每镜完整签名。
2. 只合并相邻且完全相同的签名。
3. 状态变化处切组，写 `boundary_reason`。
4. 确认第一镜 start 与最后一镜 end keyframe 均 approved。
5. 建立固定 reference order 和 `reference_stack_sha256`，并排执行角色身材/人体比例、身份/状态、地点/环境、质量、格式和时间 QA。
6. 生成一次序列 review board；用户批准整组或只指定受影响帧。
7. 计算本地 Higgsfield 适配器引用与运镜段数；超限即拆分或阻断，不能静默丢引用/删动作。

## Reference priority

序列级顺序：

1. 每个角色的统一高分辨率 3×2 身份 Inspector（第一权威）。
2. 当前人物状态。
3. 当前镜头需要的 pose/contact anchor。
4. 当前地点状态视图、plate、侧面三分之四图和主空间锚点。
5. 物件根与当前物件状态。
6. 批准 Look。
7. 当前 sequence 联合视觉锚点。
8. supplementary bridge。
9. 首/尾关键帧。
10. 六张 Inspector 确定性裁图和通过依赖闭包发现的其他干净根；裁图仅作检查/UI 辅助。

去重后保留第一次出现的职责。统一 Inspector 始终排在当前人物状态之前；裁图不能替代、重组或重新解释 Inspector。

## Adapter snapshot

2026-08-27 严格适配 Profile：`Cinema Studio 4 + Seedance 2.5`，最多 50 个参考；每个编号 Shot 只映射一条可重建摄影机路径，多路径通过编号 Shot 与 `Hard cut` 分隔。历史只读适配器为 `Popcorn:4/1`、`Cinema Studio 3:9/1`。严格导出还要求最长 30 秒、最高原生 1080p、9:16–21:9 与原生音频合同；当前 UI 与快照不符时阻断并更新，不静默改写。

## Cross-scene QA

逐组首尾和再次登场帧比较：

- 统一 Inspector、全部声明的确定性裁图、role physique、proportion signature、骨架与软组织增量。
- 人物/物件状态和关键解剖侧。
- 地点 topology、设施、尺度、锚点和材料。
- environment 的方向、积累、能见度和时间连续。
- special light 的曝光/阴影/反射波形。
- quality/capture Profile、format、camera path、temporal capture 与 blur。
- 上组动作/接触/物件位置是否在下组首帧兑现。

可见漂移即阻断；文字锁定不能覆盖像素或视频证据。
