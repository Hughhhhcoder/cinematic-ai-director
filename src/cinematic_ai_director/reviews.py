"""Atomic foundation and sequence review decisions."""

from __future__ import annotations

from .boards import *
from .core import *
from .prompts import *


def _transactional_json_replace(updates: dict[Path, dict[str, Any]]) -> None:
    """Replace a set of JSON manifests with rollback on any local failure."""
    originals = {path: path.read_bytes() for path in updates}
    staged: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, payload in updates.items():
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".txn", dir=path.parent)
            try:
                with open(fd, "w", encoding="utf-8", newline="\n", closefd=True) as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            except Exception:
                Path(temp_name).unlink(missing_ok=True)
                raise
            staged[path] = Path(temp_name)
        for path in sorted(staged, key=lambda item: item.as_posix()):
            staged[path].replace(path)
            replaced.append(path)
    except Exception:
        for path in replaced:
            path.write_bytes(originals[path])
        raise
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def _parse_selections(values: list[str]) -> dict[str, str]:
    selections: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--selection must use comparison-id=profile-id: {value}")
        comparison_id, profile_id = value.split("=", 1)
        if not comparison_id or not profile_id or comparison_id in selections:
            raise ValueError(f"invalid or duplicate --selection: {value}")
        selections[comparison_id] = profile_id
    return selections


def record_review(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2
    created_approved_files: list[Path] = []
    try:
        _require_schema_16(project_dir)
        paths = {
            "assets": project_dir / "manifests/assets.json",
            "reviews": project_dir / "manifests/reviews.json",
            "cinema": project_dir / "manifests/cinematography.json",
            "quality": project_dir / "manifests/quality.json",
            "identities": project_dir / "manifests/identities.json",
            "world": project_dir / "manifests/world-state.json",
            "spatial": project_dir / "manifests/spatial.json",
            "sequences": project_dir / "manifests/sequences.json",
            "shots": project_dir / "manifests/shots.json",
        }
        manifests = {key: _read_json_strict(path) for key, path in paths.items()}
        gate = _find_record(manifests["reviews"].get("review_gates"), args.gate, "review gate")
        if gate.get("status") != "ready_for_review":
            raise ValueError(f"gate {args.gate} must be ready_for_review, found {gate.get('status')}")
        now = utc_now()
        notes = list(args.note or [])
        affected = list(args.affected or [])
        if args.decision == "changes_requested":
            if not notes or not affected:
                raise ValueError("changes_requested requires at least one --note and one --affected id")
            gate["status"] = "changes_requested"
            gate["decision"] = "changes_requested"
            gate["decision_notes"] = notes
            gate["affected_ids"] = affected
            gate["decided_at"] = now
            _transactional_json_replace({paths["reviews"]: manifests["reviews"]})
            print(f"Recorded changes_requested for gate {args.gate}; only named dependencies should be rebuilt.")
            return 0

        selections = _parse_selections(list(args.selection or []))
        required_comparisons = set(gate.get("comparison_set_ids", []))
        if set(selections) != required_comparisons:
            raise ValueError(
                f"approved gate requires one blind selection for every comparison set; expected {sorted(required_comparisons)}, got {sorted(selections)}"
            )
        assets = {item.get("id"): item for item in manifests["assets"].get("assets", []) if isinstance(item, dict)}
        comparisons = {item.get("id"): item for item in manifests["cinema"].get("comparison_sets", []) if isinstance(item, dict)}
        profiles = {item.get("id"): item for item in manifests["cinema"].get("profiles", []) if isinstance(item, dict)}
        treatments = {item.get("id"): item for item in manifests["cinema"].get("cinematic_treatments", []) if isinstance(item, dict)}
        formats = {item.get("id"): item for item in manifests["cinema"].get("format_plans", []) if isinstance(item, dict)}
        unselected_look_ids: set[str] = set()
        selected_look_ids: set[str] = set()
        selected_treatment_ids: set[str] = set()
        rejected_treatment_ids: set[str] = set()
        for comparison_id, selected_profile_id in selections.items():
            comparison = comparisons.get(comparison_id)
            if not isinstance(comparison, dict) or comparison.get("status") != "qualified":
                raise ValueError(f"comparison {comparison_id} is missing or not qualified")
            profile_ids = comparison.get("candidate_profile_ids", [])
            asset_ids = comparison.get("candidate_asset_ids", [])
            if selected_profile_id not in profile_ids:
                raise ValueError(f"profile {selected_profile_id} is not a candidate in comparison {comparison_id}")
            position = profile_ids.index(selected_profile_id)
            selected_asset_id = asset_ids[position]
            comparison["status"] = "approved"
            comparison["selected_profile_id"] = selected_profile_id
            comparison["selected_asset_id"] = selected_asset_id
            selected_look_ids.add(selected_asset_id)
            unselected_look_ids.update(asset_id for asset_id in asset_ids if asset_id != selected_asset_id)
            for profile_id in profile_ids:
                profile = profiles.get(profile_id)
                if not isinstance(profile, dict):
                    raise ValueError(f"comparison profile is missing: {profile_id}")
                is_selected = profile_id == selected_profile_id
                profile["status"] = "approved" if is_selected else "rejected"
                profile["approved_look_test_id"] = selected_asset_id if is_selected else ""
                treatment_id = profile.get("cinematic_treatment_id")
                if isinstance(treatment_id, str):
                    (selected_treatment_ids if is_selected else rejected_treatment_ids).add(treatment_id)
        rejected_treatment_ids -= selected_treatment_ids
        for treatment_id in gate.get("treatment_ids", []):
            treatment = treatments.get(treatment_id)
            if isinstance(treatment, dict):
                treatment["status"] = "rejected" if treatment_id in rejected_treatment_ids else "approved"
        for format_id in gate.get("format_plan_ids", []):
            if format_id in formats and formats[format_id].get("status") == "qualified":
                formats[format_id]["status"] = "approved"

        for asset_id in gate.get("asset_ids", []):
            asset = assets.get(asset_id)
            if not isinstance(asset, dict):
                raise ValueError(f"gate references missing asset {asset_id}")
            if asset_id in unselected_look_ids:
                asset["status"] = "rejected"
                continue
            if asset.get("status") != "qualified":
                if asset.get("status") == "approved":
                    continue
                raise ValueError(f"gate asset {asset_id} must be qualified before approval")
            source = _active_asset_file(project_dir, asset)
            approved_relative = asset.get("approved_path")
            if not isinstance(approved_relative, str) or not approved_relative:
                raise ValueError(f"qualified asset {asset_id} requires a stable versioned approved_path")
            destination = project_dir / approved_relative
            if destination.exists():
                raise ValueError(f"approved target already exists; refusing overwrite: {approved_relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            created_approved_files.append(destination)
            asset["status"] = "approved"
            output = asset.get("generation_provenance", {}).get("output")
            if isinstance(output, dict):
                output["relative_path"] = approved_relative
                output["sha256"] = _sha256_file(destination)

        for profile in manifests["quality"].get("project_quality_profiles", []):
            if isinstance(profile, dict) and profile.get("id") in gate.get("quality_profile_ids", []):
                if profile.get("status") == "qualified":
                    profile["status"] = "approved"
        for probe in manifests["quality"].get("live_action_integration_probes", []):
            if isinstance(probe, dict) and probe.get("approval_gate_id") == args.gate:
                if probe.get("status") == "qualified":
                    probe["status"] = "approved"

        # Derived records inherit the one gate decision; no duplicate user
        # decisions are written into QA objects.
        for pack in manifests["identities"].get("identity_packs", []):
            if isinstance(pack, dict) and pack.get("approval_gate_id") == args.gate and pack.get("status") == "qualified":
                pack["status"] = "approved"
        for state in manifests["identities"].get("character_states", []):
            if isinstance(state, dict) and state.get("approval_gate_id") == args.gate and state.get("status") == "qualified":
                state["status"] = "approved"
        for collection in ("location_worlds", "location_states", "prop_states", "environmental_states", "special_lighting_events"):
            for record in manifests["world"].get(collection, []):
                if isinstance(record, dict) and record.get("approval_gate_id") == args.gate and record.get("status") == "qualified":
                    record["status"] = "approved"
        for spatial_map in manifests["spatial"].get("spatial_maps", []):
            if isinstance(spatial_map, dict) and spatial_map.get("approval_gate_id") == args.gate and spatial_map.get("status") == "qualified":
                spatial_map["status"] = "approved"

        sequence_id = gate.get("sequence_cluster_id")
        if sequence_id:
            sequence = _find_record(manifests["sequences"].get("sequence_clusters"), sequence_id, "sequence cluster")
            if sequence.get("approval_gate_id") != args.gate:
                raise ValueError(f"sequence {sequence_id} does not point back to gate {args.gate}")
            if sequence.get("status") not in {"blocked", "planned"}:
                raise ValueError(f"sequence {sequence_id} cannot become ready from status={sequence.get('status')}")
            sequence["status"] = "ready"
            for shot in manifests["shots"].get("shots", []):
                if isinstance(shot, dict) and shot.get("sequence_cluster_id") == sequence_id:
                    if shot.get("status") not in {"planned", "blocked"}:
                        raise ValueError(f"shot {shot.get('id')} cannot become ready from status={shot.get('status')}")
                    shot["status"] = "ready"

        gate["status"] = "approved"
        gate["decision"] = "approved"
        gate["decision_notes"] = notes
        gate["affected_ids"] = []
        gate["decided_at"] = now
        gate["selections"] = selections
        _transactional_json_replace({paths[key]: manifests[key] for key in paths})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        for path in created_approved_files:
            path.unlink(missing_ok=True)
        print(f"ERROR: record-review failed: {exc}", file=sys.stderr)
        return 2
    print(f"Recorded approved decision for gate {args.gate}; qualified assets and scoped records were promoted together.")
    return 0


__all__ = [name for name in globals() if not name.startswith("__")]
