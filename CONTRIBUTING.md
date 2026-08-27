# Contributing

[简体中文](CONTRIBUTING.zh-CN.md)

Thanks for helping improve evidence-driven live-action AI filmmaking. Contributions should preserve the project's offline boundary, auditability, and live-action quality floor.

## Before opening a change

- Use an issue for a new schema field, platform adapter, or workflow change.
- Do not submit scraped identities, copyrighted project prompts, proprietary media, model weights, secrets, or platform session data.
- Visual evidence must use fictional adults or references with documented rights and consent.
- A failed image may document a bug privately, but it must never be presented as an approved production result.

## Development

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/film_project.py --help
python3 scripts/build_release.py --output /tmp/cad-release
```

Optional development and documentation tools are isolated from the dependency-free runtime:

```bash
python3 -m pip install -r requirements-dev.txt
ruff check .
mkdocs build --strict
```

## Pull requests

- Keep public commands and schema compatibility unless the proposal explicitly introduces a versioned migration.
- Add behavior-focused tests for every validator, compiler, installer, or exporter change.
- Update English documentation first and the affected Chinese core mirror in the same pull request.
- Record public-source links and evidence level; do not copy long prompts or media.
- Explain security, privacy, portability, and backward-compatibility impact.

By contributing, you agree that your contribution is licensed under Apache-2.0.
