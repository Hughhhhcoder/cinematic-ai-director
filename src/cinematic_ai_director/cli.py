"""Public command-line interface."""

from __future__ import annotations

from .artifacts import *
from .core import *
from .higgsfield import *


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize, validate, or export a cinematic-ai-director project package."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new project without overwriting an existing target.")
    init_parser.add_argument("--root", help="Parent output directory; defaults to ./ai-film.")
    init_parser.add_argument("--title", required=True, help="Human-readable project title.")
    init_parser.add_argument("--slug", required=True, help="Lowercase project folder slug.")
    init_parser.add_argument("--aspect", default="16:9", help="Aspect ratio, default: 16:9.")
    init_parser.add_argument("--language", default="en", help="Interaction language, default: en.")
    init_parser.add_argument("--prompt-language", default="en", help="Generation prompt language, default: en.")

    validate_parser = subparsers.add_parser("validate", help="Validate manifests, dependencies, prompts, and continuity.")
    validate_parser.add_argument("project_dir", help="Project directory created by init.")
    validate_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")

    board_parser = subparsers.add_parser(
        "build-reference-board",
        help="Validate one authoritative single-solve identity board and deterministically crop its seven official Higgsfield views.",
    )
    board_parser.add_argument("project_dir", help="Schema v1.6 project directory.")
    board_parser.add_argument("--identity-pack", required=True, help="Qualified or approved identity-pack id.")
    board_parser.add_argument(
        "--output",
        help="Project-relative JSON crop-map path; defaults to assets/reference-boards/<identity-pack>--identity-crops-v001.json.",
    )

    compile_parser = subparsers.add_parser(
        "compile-prompts",
        help="Compile immutable v1.6 ImageGen and shot prompts from structured gate facts.",
    )
    compile_parser.add_argument("project_dir", help="Schema v1.6 project directory.")
    compile_parser.add_argument("--gate", required=True, help="Foundation or sequence review-gate id.")

    review_board_parser = subparsers.add_parser(
        "build-review-board",
        help="Build a gate-level overview and declared face/hand/material/highlight/shadow diagnostic boards.",
    )
    review_board_parser.add_argument("project_dir", help="Schema v1.6 project directory.")
    review_board_parser.add_argument("--gate", required=True, help="Foundation or sequence review-gate id.")

    record_parser = subparsers.add_parser(
        "record-review",
        help="Record one user gate decision and atomically promote or retain all scoped records.",
    )
    record_parser.add_argument("project_dir", help="Schema v1.6 project directory.")
    record_parser.add_argument("--gate", required=True, help="Foundation or sequence review-gate id.")
    record_parser.add_argument("--decision", required=True, choices=("approved", "changes_requested"))
    record_parser.add_argument(
        "--selection",
        action="append",
        default=[],
        help="Blind Look choice as comparison-id=profile-id; repeat for multiple comparisons.",
    )
    record_parser.add_argument("--note", action="append", default=[], help="Decision note; repeat as needed.")
    record_parser.add_argument(
        "--affected",
        action="append",
        default=[],
        help="Asset or record id requiring local rebuild; required for changes_requested.",
    )

    export_parser = subparsers.add_parser(
        "export-higgsfield",
        help="Create a deterministic, portable, manually executable Higgsfield production package.",
    )
    export_parser.add_argument("project_dir", help="Validated v1.6 project directory.")
    export_parser.add_argument(
        "--output",
        help="Export target; defaults to <project>/exports/higgsfield and refuses overwrite.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return init_project(args)
    if args.command == "validate":
        return validate_project(Path(args.project_dir).expanduser(), args.as_json)
    if args.command == "build-reference-board":
        return build_reference_board(args)
    if args.command == "compile-prompts":
        return compile_prompts(args)
    if args.command == "build-review-board":
        return build_review_board(args)
    if args.command == "record-review":
        return record_review(args)
    if args.command == "export-higgsfield":
        return export_higgsfield(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
