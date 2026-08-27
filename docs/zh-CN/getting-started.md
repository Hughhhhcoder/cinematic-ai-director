# 快速开始

## 环境要求

- Python 3.10 或更高版本
- 可使用内置 ImageGen 的 Codex（只有需要生成静态资产时才需要）
- macOS、Windows 或 Linux

运行时只使用 Python 标准库，不需要外部图片 API。

## 安装为 Codex Skill

```bash
git clone https://github.com/Hughhhhcoder/cinematic-ai-director.git
cd cinematic-ai-director
python3 scripts/install_skill.py install
```

安装器优先使用 `CODEX_HOME`，否则安装到 `~/.codex/skills/cinematic-ai-director`。默认拒绝覆盖；显式替换时会先备份，安装失败则自动回滚：

```bash
python3 scripts/install_skill.py install --replace
python3 scripts/install_skill.py verify
```

也可以安装命令行入口：

```bash
python3 -m pip install .
cinematic-ai-director --help
```

## 新建项目

```bash
python3 scripts/film_project.py init \
  --title "Night Shift" \
  --slug night-shift \
  --root ./ai-film

python3 scripts/film_project.py validate ./ai-film/night-shift
```

然后在 Codex 中调用 `$cinematic-ai-director` 并提供剧本、故事梗概或已有项目目录。默认中文沟通时以中文反馈，生图与视频模型提示使用英文。

## 审批节奏

正常流程只要求：

1. 一次 Foundation 审批：现实简报、角色与身材、单张 4×2 统一身份检查板及确定性裁图、地点包、空间锚点、画幅和盲选 Look。
2. 每个 `sequence_cluster` 一次审批：联合锚点、状态、Photoboard、关键帧、空间图和提示摘要。

某一张需要修改时，只返工该资产及其直接依赖，不推翻已经批准的无关内容。

## 常用命令

```text
init                    初始化 Schema 1.6 项目且不覆盖旧目录
validate                审计文件、依赖、状态、QA、提示与连续性
build-reference-board   从一张批准 Inspector 无重绘、无缩放裁出七张 PNG
compile-prompts         从结构化事实确定性编译版本化提示
build-review-board      生成总览及脸、手、材质、高光、暗部诊断页
record-review           原子记录门级批准或修改请求
export-higgsfield       生成离线 Higgsfield 制作包与校验文件
```

完整参数请运行 `python3 scripts/film_project.py <command> --help`。
