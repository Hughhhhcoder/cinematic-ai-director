# Getting started

## Requirements

- Codex with built-in ImageGen for still-asset production.
- Python 3.10 or newer for the offline toolkit.
- No Python runtime dependencies, API keys, or Higgsfield credentials.

## Install the Skill

```bash
git clone https://github.com/Hughhhhcoder/cinematic-ai-director.git
cd cinematic-ai-director
python3 scripts/install_skill.py install
python3 scripts/install_skill.py verify
```

If an installation already exists, replacement is explicit and recoverable:

```bash
python3 scripts/install_skill.py install --replace
```

The installer respects `CODEX_HOME`; otherwise it targets `~/.codex/skills/cinematic-ai-director`. It validates a SHA-256 runtime manifest before completing and creates a timestamped backup before replacement.

## Start a project

```bash
python3 scripts/film_project.py init \
  --title "Night Shift" \
  --slug night-shift \
  --root ./ai-film \
  --aspect 16:9 \
  --language en \
  --prompt-language en
```

The initializer refuses to overwrite an existing project. It creates schema `1.6`, empty manifests, QA records, prompts, asset responsibilities, and an edit-plan skeleton.

## Invoke in Codex

Provide the live-action story or script and say:

```text
Use $cinematic-ai-director to build this as a live-action film project.
Keep generation prompts in English and present only the Foundation and sequence gates.
```

Codex derives the reality, casting, role physique, world design, state timeline, project quality profile, format, and production sequence before it generates dependent assets.

## Validate at any point

```bash
python3 scripts/film_project.py validate ./ai-film/night-shift
python3 scripts/film_project.py validate ./ai-film/night-shift --json
```

Validation is read-only. Schema v1.0–v1.5 returns `LEGACY_SCHEMA` and is not migrated.

## Review and export

```bash
python3 scripts/film_project.py compile-prompts <project> --gate <gate-id>
python3 scripts/film_project.py build-review-board <project> --gate <gate-id>
python3 scripts/film_project.py record-review <project> --gate <gate-id> --decision approved
python3 scripts/film_project.py export-higgsfield <project>
python3 <project>/exports/higgsfield/verify_package.py
```

The last command verifies local integrity only. You remain responsible for manually binding references and generating on the target platform.
