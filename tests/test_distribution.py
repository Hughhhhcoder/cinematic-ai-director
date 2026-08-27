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
            "assets/quality-evidence/.gitkeep",
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
            self.assertEqual(payload["version"], "1.6.0")
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
                outputs.append(output / "cinematic-ai-director-v1.6.0.zip")
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

    def test_compact_showcase_has_exactly_three_hashed_originals(self) -> None:
        evidence = json.loads((ROOT / "showcase" / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["showcase_profile"], "compact-release-evidence-v1.6")
        self.assertFalse(evidence["pixel_reproducible"])
        self.assertEqual(
            [item["kind"] for item in evidence["assets"]],
            ["identity", "empty_scene", "narrative"],
        )
        originals = sorted((ROOT / "showcase" / "originals").glob("**/*.png"))
        authority_originals = [path for path in originals if "identity-crops" not in path.parts]
        self.assertEqual(len(authority_originals), 3)
        for item in evidence["assets"]:
            original = ROOT / item["original_path"]
            prompt = ROOT / item["prompt_path"]
            derivative = ROOT / item["publication_derivative_path"]
            self.assertEqual(digest(original), item["original_sha256"])
            self.assertEqual(digest(prompt), item["prompt_sha256"])
            self.assertEqual(digest(derivative), item["publication_derivative_sha256"])
            dynamic_range = item["qa"]["finite_dynamic_range"]
            self.assertEqual(dynamic_range["policy"], "finite_scene_referred")
            self.assertFalse(dynamic_range["local_tone_mapping_detected"])
            self.assertFalse(dynamic_range["multi_exposure_hdr_merge"])
        crop_map = evidence["identity_crops"]
        self.assertEqual(crop_map["operation"], "exact-cell-crop-no-resample-no-redraw")
        self.assertEqual(len(crop_map["crops"]), 7)
        for crop in crop_map["crops"]:
            self.assertEqual(digest(ROOT / crop["path"]), crop["sha256"])


if __name__ == "__main__":
    unittest.main()
