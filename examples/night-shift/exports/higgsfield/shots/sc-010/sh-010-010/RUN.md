# sh-010-010 执行卡

1. 先核对 `spatial-map.json`，再按 `references.csv` 的 rank 顺序加载参考；不得跳过 `required=true`。
2. 确认 `location_shot_view`、`location_three_quarter` 和 `spatial_anchor` 的句柄与文件无误，再粘贴 `prompt.txt` 并按 `settings.json` 配置当前 Cinema Studio。
3. 核对 `format-plan.json` 不含烧入黑边，`camera-path.json` 的起止标记和承托可执行，`temporal-lock.json` 的快门公式与模糊方向一致；再核对 `dynamic-range.json` 明确保护对象、允许溢出的亮部和允许失去细节的暗部。
4. 镜头时长：4.0 秒；机位轴线：doorway-to-window；运动：locked off；环境：env-workshop-clear。
5. 首条只作校准。若身份比例、皮肤/材质、空间地理、接触关系、天气响应、焦点、动态模糊或有限动态范围取舍错误，停止批量生成并回到对应批准资产或镜头提示修订。
6. 通过后以 `sh-010-010--take-001` 起顺序保存，不覆盖旧 take，并将视频交回 Skill 写入 `takes.json` 做时间 QA。
