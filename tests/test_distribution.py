"""Distribution, install, and source-hygiene tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cinematic_ai_director.validation import portable_manifest_path  # noqa: E402

INSTALLER = ROOT / "scripts" / "install_skill.py"
RELEASE_BUILDER = ROOT / "scripts" / "build_release.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DistributionTests(unittest.TestCase):
    def test_manifest_path_policy_is_host_separator_independent(self) -> None:
        self.assertEqual(
            portable_manifest_path(r"assets\characters\identity-inspectors\hero.png"),
            "assets/characters/identity-inspectors/hero.png",
        )

    def test_public_example_preserves_required_empty_directories_in_git(self) -> None:
        sentinels = (
            "assets/style/.gitkeep",
            "assets/characters/identity-packs/.gitkeep",
            "assets/characters/pose-anchors/.gitkeep",
            "assets/storyboards/.gitkeep",
            "assets/key-art/.gitkeep",
            "prompts/images/identity-packs/.gitkeep",
            "prompts/images/identity-views/.gitkeep",
            "prompts/images/pose-anchors/.gitkeep",
            "prompts/images/states/.gitkeep",
            "prompts/compiled/.gitkeep",
        )
        example = ROOT / "examples" / "night-shift"
        self.assertTrue(all((example / relative).is_file() for relative in sentinels))

    def test_install_and_verify_are_cross_platform_path_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-install-") as directory:
            home = Path(directory)
            installed = run(sys.executable, str(INSTALLER), "install", "--codex-home", str(home))
            self.assertEqual(installed.returncode, 0, installed.stderr)
            verified = run(sys.executable, str(INSTALLER), "verify", "--codex-home", str(home))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            payload = json.loads((home / "skills" / "cinematic-ai-director" / "runtime-manifest.json").read_text())
            self.assertEqual(payload["version"], "1.6.6")
            self.assertTrue(all(not Path(item["path"]).is_absolute() for item in payload["files"]))

    def test_install_refuses_overwrite_and_replace_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-replace-") as directory:
            home = Path(directory)
            first = run(sys.executable, str(INSTALLER), "install", "--codex-home", str(home))
            self.assertEqual(first.returncode, 0, first.stderr)
            refused = run(sys.executable, str(INSTALLER), "install", "--codex-home", str(home))
            self.assertEqual(refused.returncode, 2)
            replaced = run(sys.executable, str(INSTALLER), "install", "--codex-home", str(home), "--replace")
            self.assertEqual(replaced.returncode, 0, replaced.stderr)
            backups = list((home / "skills").glob("cinematic-ai-director.backup-*") )
            self.assertEqual(len(backups), 1)

    def test_verify_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-tamper-") as directory:
            home = Path(directory)
            self.assertEqual(run(sys.executable, str(INSTALLER), "install", "--codex-home", str(home)).returncode, 0)
            skill = home / "skills" / "cinematic-ai-director"
            (skill / "SKILL.md").write_text("tampered\n", encoding="utf-8")
            verified = run(sys.executable, str(INSTALLER), "verify", "--codex-home", str(home))
            self.assertEqual(verified.returncode, 1)
            self.assertIn("checksum mismatch", verified.stderr)

    def test_release_archive_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-release-") as directory:
            root = Path(directory)
            outputs = []
            for index in (1, 2):
                output = root / f"dist-{index}"
                manifest = root / f"manifest-{index}.json"
                result = run(
                    sys.executable,
                    str(RELEASE_BUILDER),
                    "--output",
                    str(output),
                    "--manifest-output",
                    str(manifest),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(output / "cinematic-ai-director-v1.6.6.zip")
            self.assertEqual(digest(outputs[0]), digest(outputs[1]))

    def test_runtime_source_contains_no_private_machine_paths_or_caches(self) -> None:
        forbidden = ("/Users/Hughhhh", "Documents/ChatGPT", "generated_images", "missing-forty-seven-seconds")
        roots = [ROOT / "SKILL.md", ROOT / "agents", ROOT / "assets", ROOT / "references", ROOT / "scripts" / "film_project.py", ROOT / "src"]
        for item in roots:
            files = item.rglob("*") if item.is_dir() else (item,)
            for path in files:
                if not path.is_file() or path.suffix in {".pyc", ".pyo"} or "__pycache__" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertFalse(any(token in text for token in forbidden), path)

    def test_failed_release_visuals_are_withheld_instead_of_published(self) -> None:
        evidence = json.loads((ROOT / "showcase" / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["release"], "1.6.6")
        self.assertEqual(evidence["status"], "withheld_by_quality_gate")
        self.assertEqual(evidence["backend"], "builtin-imagegen")
        self.assertFalse(evidence["pixel_reproducible"])
        self.assertEqual(evidence["published_assets"], [])
        self.assertFalse(evidence["failed_files_published"])
        self.assertFalse(evidence["downstream_generation_performed"])
        self.assertEqual(evidence["summary"], {"attempts": 3, "passed": 0, "rejected": 3})
        self.assertEqual(
            {item["id"]: item["count"] for item in evidence["failure_classes"]},
            {
                "insufficient_native_full_body_pixel_coverage": 1,
                "topographic_contour_or_maze_skin_texture": 2,
            },
        )
        public_rasters = [
            path
            for path in (ROOT / "showcase").rglob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ]
        self.assertEqual(public_rasters, [])


if __name__ == "__main__":
    unittest.main()
