# CLI and schema

## Commands

| Command | Mutates project? | Purpose |
|---|---:|---|
| `init` | Yes, new target only | Create schema v1.6 and refuse overwrite |
| `validate` | No | Audit layout, files, references, states, QA, prompts, continuity, and gates |
| `build-reference-board` | Yes, new output only | Deterministically crop seven PNG views from one approved 4×2 Inspector |
| `compile-prompts` | Yes, versioned output | Compile image and shot prompts from facts; refuse overwrite |
| `build-review-board` | Yes, new output only | Arrange selected originals and diagnostic crops without repainting |
| `record-review` | Yes, atomically | Approve a gate or record scoped changes and roll back on failure |
| `export-higgsfield` | Yes, new output only | Build deterministic portable work orders and checksums |

## Project package

Schema v1.6 separates project metadata; assets; cinematography; space; shots; continuity; identities; world state; sequences; takes; quality; candidates; and review gates. Prompt files, QA evidence, review boards, and exports remain separate from authoritative facts.

Ready shots must bind exact IDs rather than free-text names. Validators check asset duties, legal provenance, prompt strategy and headings, identity and state deltas, role physique, spatial marks, profile/format/environment, per-asset and per-shot finite dynamic-range plans, camera/temporal/blur physics, sequence signatures, review decisions, adapter limits, and machine-specific path leakage.

See [`references/project-schema.md`](https://github.com/Hughhhhcoder/cinematic-ai-director/blob/main/references/project-schema.md) for the complete field protocol.

## Compatibility

Schema v1.0–v1.5 is detected and reported as `LEGACY_SCHEMA`; it is never migrated or modified. New schema versions must define explicit migration and rollback policy before implementation.
