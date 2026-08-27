# 贡献指南

[English](CONTRIBUTING.md)

感谢你帮助改进以证据为基础的真人 AI 影视流程。所有贡献必须保留离线边界、可审计性和真人实拍质量底线。

## 提交前

- 新 Schema 字段、平台适配器或流程改变先建立 Issue。
- 禁止提交网页抓取人物、他人完整提示词、专有媒体、模型权重、密钥或平台会话数据。
- 视觉证据只能使用虚构成年人，或拥有明确使用权与真人同意的参考。
- 失败图可以私下证明缺陷，但不能被包装成已批准效果。

## 开发检查

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/film_project.py --help
python3 scripts/build_release.py --output /tmp/cad-release
python3 -m pip install -r requirements-dev.txt
ruff check .
mkdocs build --strict
```

Pull Request 必须补充行为测试、英语主文档及受影响的中文核心镜像，并说明安全、隐私、便携性和兼容性影响。贡献默认以 Apache-2.0 授权。
