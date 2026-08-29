"""Deterministic PNG decoding and production review-board builders."""

from __future__ import annotations

from .core import *


def portable_write_text(path: Path, value: str) -> None:
    """Write UTF-8 text with stable LF line endings on every supported OS."""
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)


def portable_write_json(path: Path, value: Any) -> None:
    portable_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
REFERENCE_BOARD_WIDTH = 3200
REFERENCE_BOARD_HEIGHT = 1800
REFERENCE_BOARD_COLUMNS = 4  # legacy review-board rendering default; identity cropper is profile-driven
REFERENCE_BOARD_ROWS = 2
REFERENCE_BOARD_MARGIN = 36


def _png_paeth(a: int, b: int, c: int) -> int:
    prediction = a + b - c
    distance_a = abs(prediction - a)
    distance_b = abs(prediction - b)
    distance_c = abs(prediction - c)
    if distance_a <= distance_b and distance_a <= distance_c:
        return a
    if distance_b <= distance_c:
        return b
    return c


def _decode_png_rgb(path: Path) -> tuple[int, int, bytes]:
    """Decode one deliberately narrow PNG subset without silently transcoding.

    Reference boards accept only non-interlaced, 8-bit RGB or RGBA PNG inputs.
    This keeps behavior deterministic and makes unsupported files fail loudly.
    """
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"reference-board input is not a PNG file: {path.name}")
    offset = len(PNG_SIGNATURE)
    ihdr: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    saw_end = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        payload_start = offset + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        if crc_end > len(data):
            raise ValueError(f"truncated PNG chunk in {path.name}")
        payload = data[payload_start:payload_end]
        expected_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ValueError(f"PNG CRC mismatch in {path.name}")
        if chunk_type == b"IHDR":
            if length != 13 or ihdr is not None:
                raise ValueError(f"invalid PNG IHDR in {path.name}")
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"IEND":
            saw_end = True
            break
        offset = crc_end
    if ihdr is None or not compressed or not saw_end:
        raise ValueError(f"incomplete PNG file: {path.name}")
    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid PNG dimensions in {path.name}")
    if bit_depth != 8 or color_type not in {2, 6} or compression != 0 or filter_method != 0 or interlace != 0:
        raise ValueError(
            f"unsupported PNG {path.name}: require non-interlaced 8-bit RGB or RGBA; "
            f"got bit_depth={bit_depth}, color_type={color_type}, interlace={interlace}"
        )
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        raise ValueError(f"cannot decompress PNG {path.name}: {exc}") from exc
    expected_size = height * (stride + 1)
    if len(raw) != expected_size:
        raise ValueError(f"unexpected PNG scanline size in {path.name}")
    decoded_rows: list[bytearray] = []
    cursor = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor:cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            up_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _png_paeth(left, up, up_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type} in {path.name}")
            row[index] = (value + predictor) & 0xFF
        decoded_rows.append(row)
        previous = row
    rgb = bytearray(width * height * 3)
    destination = 0
    for row in decoded_rows:
        for x in range(width):
            source = x * channels
            if channels == 3:
                rgb[destination:destination + 3] = row[source:source + 3]
            else:
                alpha = row[source + 3]
                inverse = 255 - alpha
                rgb[destination] = (row[source] * alpha + 255 * inverse + 127) // 255
                rgb[destination + 1] = (row[source + 1] * alpha + 255 * inverse + 127) // 255
                rgb[destination + 2] = (row[source + 2] * alpha + 255 * inverse + 127) // 255
            destination += 3
    return width, height, bytes(rgb)


def _resize_rgb_nearest(
    width: int,
    height: int,
    pixels: bytes,
    maximum_width: int,
    maximum_height: int,
) -> tuple[int, int, bytes]:
    scale = min(maximum_width / width, maximum_height / height)
    output_width = max(1, int(round(width * scale)))
    output_height = max(1, int(round(height * scale)))
    source_x = [min(width - 1, int((x + 0.5) * width / output_width)) for x in range(output_width)]
    resized = bytearray(output_width * output_height * 3)
    destination = 0
    for y in range(output_height):
        source_y = min(height - 1, int((y + 0.5) * height / output_height))
        row_offset = source_y * width * 3
        for x in source_x:
            source = row_offset + x * 3
            resized[destination:destination + 3] = pixels[source:source + 3]
            destination += 3
    return output_width, output_height, bytes(resized)


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def _encode_png_rgb(width: int, height: int, pixels: bytes) -> bytes:
    if len(pixels) != width * height * 3:
        raise ValueError("RGB byte count does not match PNG dimensions")
    scanlines = bytearray()
    stride = width * 3
    for y in range(height):
        scanlines.append(0)
        start = y * stride
        scanlines.extend(pixels[start:start + stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _detect_horizontal_gutter_split(
    width: int,
    height: int,
    pixels: bytes,
) -> tuple[int, dict[str, Any]]:
    """Find the approved white gutter between identity-board rows.

    ImageGen can preserve the official two-row role order while making the
    full-body row slightly taller than the portrait row.  Equal-height crops
    can then amputate boots even though the authority board is otherwise
    valid.  This deterministic detector searches only near the canvas centre,
    records the accepted white run, and never interprets or redraws a person.
    """
    if len(pixels) != width * height * 3:
        raise ValueError("identity inspector RGB byte count does not match dimensions")
    search_start = max(1, int(height * 0.40))
    search_end = min(height - 1, int(height * 0.62))
    maximum_nonwhite = max(2, int(round(width * 0.02)))
    qualifying: list[int] = []
    for y in range(search_start, search_end):
        nonwhite = 0
        row_start = y * width * 3
        for x in range(width):
            offset = row_start + x * 3
            red, green, blue = pixels[offset:offset + 3]
            if min(red, green, blue) < 238 or max(red, green, blue) - min(red, green, blue) > 10:
                nonwhite += 1
                if nonwhite > maximum_nonwhite:
                    break
        if nonwhite <= maximum_nonwhite:
            qualifying.append(y)
    runs: list[tuple[int, int]] = []
    if qualifying:
        run_start = qualifying[0]
        previous = qualifying[0]
        for value in qualifying[1:]:
            if value != previous + 1:
                runs.append((run_start, previous))
                run_start = value
            previous = value
        runs.append((run_start, previous))
    runs = [run for run in runs if run[1] - run[0] + 1 >= 2]
    if not runs:
        raise ValueError(
            "identity inspector has no deterministic near-white horizontal gutter near the canvas centre"
        )
    centre = height / 2
    selected = min(
        runs,
        key=lambda run: (abs(((run[0] + run[1] + 1) / 2) - centre), -(run[1] - run[0] + 1)),
    )
    split = (selected[0] + selected[1] + 1) // 2
    if split <= 0 or split >= height:
        raise ValueError("detected identity-board row split is outside the canvas")
    return split, {
        "method": "central-near-white-gutter-v1.6.1",
        "search_rows_px": [search_start, search_end],
        "accepted_gutter_rows_px": [selected[0], selected[1] + 1],
        "split_y_px": split,
        "near_white_min_channel": 238,
        "maximum_nonwhite_pixels_per_row": maximum_nonwhite,
    }


def build_reference_board(args: argparse.Namespace) -> int:
    """Crop upload/check views from one approved single-solve board.

    The ImageGen board is the first and only identity authority.  This command
    never composes or repaints a person; it extracts the declared supported
    reference-sheet cells byte-deterministically into convenience files.
    """
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2
    project_path = project_dir / "project.json"
    identities_path = project_dir / "manifests/identities.json"
    assets_path = project_dir / "manifests/assets.json"
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
        identities = json.loads(identities_path.read_text(encoding="utf-8"))
        asset_manifest = json.loads(assets_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read project manifests: {exc}", file=sys.stderr)
        return 2
    version = project.get("schema_version")
    if version in LEGACY_SCHEMA_VERSIONS:
        print(f"ERROR: LEGACY_SCHEMA {version}; v1.6 will not migrate or modify this project.", file=sys.stderr)
        return 1
    if version != SCHEMA_VERSION or identities.get("schema_version") != SCHEMA_VERSION:
        print("ERROR: build-reference-board requires a schema 1.6 project.", file=sys.stderr)
        return 1
    pack = next(
        (
            item for item in identities.get("identity_packs", [])
            if isinstance(item, dict) and item.get("id") == args.identity_pack
        ),
        None,
    )
    if not isinstance(pack, dict):
        print(f"ERROR: identity pack does not exist: {args.identity_pack}", file=sys.stderr)
        return 1
    if pack.get("status") not in {"qualified", "approved"}:
        print(f"ERROR: identity pack must be qualified or approved: {args.identity_pack}", file=sys.stderr)
        return 1
    assets = {
        item.get("id"): item
        for item in asset_manifest.get("assets", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    inspector_id = pack.get("identity_inspector_asset_id")
    inspector = assets.get(inspector_id)
    if not isinstance(inspector, dict) or inspector.get("type") != "character_identity_inspector":
        print("ERROR: identity pack has no single-solve identity inspector authority.", file=sys.stderr)
        return 1
    if inspector.get("status") not in {"qualified", "approved"}:
        print("ERROR: identity inspector must pass QA before any view can be cropped.", file=sys.stderr)
        return 1
    if inspector.get("identity_pack_id") != args.identity_pack:
        print("ERROR: identity inspector points to a different identity pack.", file=sys.stderr)
        return 1
    layout = inspector.get("identity_inspector_layout") if isinstance(inspector.get("identity_inspector_layout"), dict) else {}
    layout_profile = layout.get("profile")
    layout_spec = identity_layout_spec(layout_profile)
    if layout_spec is None:
        print(f"ERROR: unsupported identity inspector layout: {layout_profile}", file=sys.stderr)
        return 1
    grid = layout_spec.get("grid")
    roles = identity_roles_for_layout(layout_profile)
    if not isinstance(grid, list) or len(grid) != 2 or grid[1] != 2 or not roles:
        print("ERROR: identity inspector layout must declare a supported two-row grid.", file=sys.stderr)
        return 1
    source_relative = inspector.get("approved_path") if inspector.get("status") == "approved" else inspector.get("candidate_path")
    if not isinstance(source_relative, str) or not source_relative:
        print("ERROR: identity inspector has no active PNG path.", file=sys.stderr)
        return 1
    source_rel_path = Path(source_relative)
    if source_rel_path.is_absolute() or ".." in source_rel_path.parts or source_rel_path.suffix.lower() != ".png":
        print("ERROR: identity inspector must use a project-relative PNG file.", file=sys.stderr)
        return 1
    source = project_dir / source_rel_path
    if not source.is_file():
        print(f"ERROR: identity inspector file is missing: {source_relative}", file=sys.stderr)
        return 1
    board_bytes = source.read_bytes()
    board_hash = hashlib.sha256(board_bytes).hexdigest()
    provenance = inspector.get("generation_provenance") if isinstance(inspector.get("generation_provenance"), dict) else {}
    recorded_output = provenance.get("output") if isinstance(provenance.get("output"), dict) else {}
    if recorded_output.get("sha256") != board_hash:
        print("ERROR: identity inspector hash does not match its provenance.", file=sys.stderr)
        return 1
    view_map = pack.get("identity_view_asset_ids")
    if not isinstance(view_map, dict) or set(view_map) != set(roles):
        print("ERROR: identity pack crop roles do not match its unified board layout.", file=sys.stderr)
        return 1
    map_relative = (
        Path(args.output)
        if args.output
        else Path("assets/reference-boards") / f"{args.identity_pack}--identity-crops-v001.json"
    )
    if map_relative.is_absolute() or ".." in map_relative.parts or map_relative.suffix.lower() != ".json":
        print("ERROR: --output must be a project-relative .json crop-map path.", file=sys.stderr)
        return 2
    map_path = project_dir / map_relative
    if map_path.exists():
        print(f"ERROR: crop map already exists; refusing to overwrite: {map_relative}", file=sys.stderr)
        return 2

    crop_assets: list[tuple[str, dict[str, Any], Path]] = []
    for role in roles:
        crop_asset_id = view_map.get(role)
        crop_asset = assets.get(crop_asset_id)
        if not isinstance(crop_asset, dict):
            print(f"ERROR: missing deterministic crop asset for {role}.", file=sys.stderr)
            return 1
        expected_type = "character_face_anchor" if role == "portrait_front" else "character_body_anchor" if role == "full_front" else "character_identity_view"
        if crop_asset.get("type") != expected_type:
            print(f"ERROR: {crop_asset_id} has the wrong asset type for {role}.", file=sys.stderr)
            return 1
        if crop_asset.get("status") != "planned":
            print(f"ERROR: crop asset {crop_asset_id} is not planned; refusing overwrite.", file=sys.stderr)
            return 2
        if crop_asset.get("generator") != "deterministic-crop" or crop_asset.get("mode") != "crop":
            print(f"ERROR: crop asset {crop_asset_id} must use deterministic-crop/crop.", file=sys.stderr)
            return 1
        if crop_asset.get("identity_view_role") != role:
            print(f"ERROR: crop asset {crop_asset_id} role mismatch.", file=sys.stderr)
            return 1
        if crop_asset.get("derived_from") != inspector_id:
            print(f"ERROR: crop asset {crop_asset_id} must derive directly from the inspector.", file=sys.stderr)
            return 1
        if crop_asset.get("reference_asset_ids") != [inspector_id] or crop_asset.get("root_reference_ids") != [inspector_id]:
            print(f"ERROR: crop asset {crop_asset_id} must reference only the inspector authority.", file=sys.stderr)
            return 1
        crop_relative = crop_asset.get("candidate_path")
        if not isinstance(crop_relative, str) or not crop_relative:
            print(f"ERROR: crop asset {crop_asset_id} has no candidate_path.", file=sys.stderr)
            return 1
        crop_rel_path = Path(crop_relative)
        if crop_rel_path.is_absolute() or ".." in crop_rel_path.parts or crop_rel_path.suffix.lower() != ".png":
            print(f"ERROR: crop asset {crop_asset_id} must use a project-relative PNG candidate_path.", file=sys.stderr)
            return 1
        crop_path = project_dir / crop_rel_path
        if crop_path.exists():
            print(f"ERROR: crop target already exists; refusing overwrite: {crop_relative}", file=sys.stderr)
            return 2
        crop_assets.append((role, crop_asset, crop_path))

    created: list[Path] = []
    try:
        width, height, pixels = _decode_png_rgb(source)
        columns = int(grid[0])
        if width % columns:
            raise ValueError(f"identity inspector width must divide exactly into {columns} columns")
        cell_width = width // columns
        resolution_policy = project.get("resolution_policy") if isinstance(project.get("resolution_policy"), dict) else None
        policy_applies = isinstance(resolution_policy, dict) and resolution_policy.get("mode") == "strict_native_detail_v1.6.6"
        if policy_applies and valid_timestamp(resolution_policy.get("effective_at")) and valid_timestamp(inspector.get("created_at")):
            policy_applies = datetime.fromisoformat(str(inspector.get("created_at")).replace("Z", "+00:00")) >= datetime.fromisoformat(str(resolution_policy.get("effective_at")).replace("Z", "+00:00"))
        if policy_applies:
            minimum_board = resolution_policy.get("minimum_identity_board_px", [1536, 1024])
            if width < minimum_board[0] or height < minimum_board[1]:
                raise ValueError(f"identity inspector is below the native {minimum_board[0]}x{minimum_board[1]} board floor")
            if cell_width < resolution_policy.get("minimum_identity_cell_width_px", 512):
                raise ValueError("identity inspector cells are too narrow for high-detail inspection")
        row_split, gutter_detection = _detect_horizontal_gutter_split(width, height, pixels)
        row_tops = (0, row_split)
        row_heights = (row_split, height - row_split)
        slots: list[dict[str, Any]] = []
        source_hashes: dict[str, str] = {}
        for slot_index, (role, crop_asset, crop_path) in enumerate(crop_assets):
            column = slot_index % columns
            row = slot_index // columns
            left = column * cell_width
            top = row_tops[row]
            cell_height = row_heights[row]
            crop_pixels = bytearray(cell_width * cell_height * 3)
            for crop_y in range(cell_height):
                source_start = ((top + crop_y) * width + left) * 3
                destination_start = crop_y * cell_width * 3
                crop_pixels[destination_start:destination_start + cell_width * 3] = pixels[source_start:source_start + cell_width * 3]
            crop_bytes = _encode_png_rgb(cell_width, cell_height, bytes(crop_pixels))
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            crop_path.write_bytes(crop_bytes)
            created.append(crop_path)
            crop_hash = hashlib.sha256(crop_bytes).hexdigest()
            source_hashes[role] = crop_hash
            crop_asset["status"] = "qualified"
            crop_asset["prompt_path"] = ""
            crop_asset["candidate_set_id"] = ""
            crop_asset["generation_provenance"] = {
                "backend": "deterministic-crop",
                "reproducibility_class": "source_exact",
                "pixel_reproducible": True,
                "operation": "crop",
                "prompt_sha256": "",
                "reference_order": [inspector_id],
                "reference_inputs": [
                    {"asset_id": inspector_id, "relative_path": source_relative, "sha256": board_hash}
                ],
                "crop_box_px": [left, top, cell_width, cell_height],
                "output": {
                    "relative_path": crop_asset["candidate_path"],
                    "sha256": crop_hash,
                    "width_px": cell_width,
                    "height_px": cell_height,
                    "color_mode": "RGB",
                    "mime_type": "image/png",
                },
                "software_agent": "cinematic-ai-director deterministic PNG cropper",
            }
            crop_asset["photographic_qa"] = inspector.get("photographic_qa")
            crop_asset["geometry_qa"] = inspector.get("geometry_qa")
            crop_asset["live_action_quality_qa"] = inspector.get("live_action_quality_qa")
            inspector_resolution = inspector.get("resolution_qa") if isinstance(inspector.get("resolution_qa"), dict) else {}
            inspector_coverage = inspector_resolution.get("subject_coverage_px") if isinstance(inspector_resolution.get("subject_coverage_px"), dict) else {}
            role_coverage = {}
            if role.startswith("full_"):
                role_coverage["full_body_subject_height_px"] = int(inspector_coverage.get("full_body_subject_height_px", 0))
            if role.startswith("portrait_"):
                role_coverage["portrait_face_height_px"] = int(inspector_coverage.get("portrait_face_height_px", 0))
            if policy_applies:
                crop_asset["resolution_qa"] = {
                    "mode": "native_detail",
                    "source_dimensions_px": [width, height],
                    "delivered_dimensions_px": [cell_width, cell_height],
                    "subject_coverage_px": role_coverage,
                    "native_generation_or_source": True,
                    "dimension_only_upscale": False,
                    "checks": {name: "pass" for name in RESOLUTION_QA_CHECKS},
                    "verdict": "pass",
                    "hard_failures": [],
                    "notes": ["Exact non-resampled crop inherited from the visually approved unified identity board."],
                    "checked_at": inspector_resolution.get("checked_at", ""),
                    "reviewer": inspector_resolution.get("reviewer", "codex-visual"),
                }
            slots.append(
                {
                    "slot": slot_index + 1,
                    "row": row + 1,
                    "column": column + 1,
                    "role": role,
                    "asset_id": crop_asset.get("id"),
                    "crop_box_px": [left, top, cell_width, cell_height],
                    "crop_sha256": crop_hash,
                }
            )
        map_path.parent.mkdir(parents=True, exist_ok=True)
        portable_write_json(
            map_path,
            {
                "schema_version": SCHEMA_VERSION,
                "identity_pack_id": args.identity_pack,
                "identity_inspector_asset_id": inspector_id,
                "layout_profile": layout_profile,
                "canvas_px": [width, height],
                "grid": grid,
                "row_split_px": row_split,
                "gutter_detection": gutter_detection,
                "background": "pure_white",
                "authoritative": True,
                "authority_sha256": board_hash,
                "generation": "one-imagegen-call-then-deterministic-crops",
                "blank_slot": layout_spec.get("blank_slot"),
                "slots": slots,
            },
        )
        created.append(map_path)
        pack["reference_board"] = {
            "status": "ready",
            "relative_path": source_relative,
            "sha256": board_hash,
            "source_sha256s": source_hashes,
            "layout_profile": layout_profile,
            "authoritative": True,
            "crop_map_path": map_relative.as_posix(),
            "row_split_px": row_split,
        }
        write_json(assets_path, asset_manifest)
        write_json(identities_path, identities)
    except Exception as exc:
        for path in created:
            path.unlink(missing_ok=True)
        print(f"ERROR: identity crop build failed: {exc}", file=sys.stderr)
        return 2
    print(f"Validated authoritative single-solve identity board: {source}")
    print(f"Created {len(roles)} deterministic inspection/upload crops and map: {map_path}")
    print("The unified board remains the first and only identity authority; no ImageGen repaint was performed.")
    return 0


def _read_json_strict(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _require_schema_16(project_dir: Path) -> dict[str, Any]:
    project = _read_json_strict(project_dir / "project.json")
    version = project.get("schema_version")
    if version in LEGACY_SCHEMA_VERSIONS:
        raise ValueError(f"LEGACY_SCHEMA {version}; v1.6 never migrates or modifies v1.0-v1.5 projects")
    if version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    return project


def _find_record(rows: Any, record_id: str, label: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError(f"{label} collection is not an array")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == record_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {label} {record_id}, found {len(matches)}")
    return matches[0]


def _candidate_variants(candidate_set: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for batch in candidate_set.get("batches", []) if isinstance(candidate_set.get("batches"), list) else []:
        if isinstance(batch, dict) and isinstance(batch.get("candidates"), list):
            variants.extend(item for item in batch["candidates"] if isinstance(item, dict))
    return variants


def _active_asset_file(project_dir: Path, asset: dict[str, Any]) -> Path:
    status = asset.get("status")
    relative = asset.get("approved_path") if status in {"approved", "superseded"} else asset.get("candidate_path")
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"asset {asset.get('id')} has no active image path")
    path = project_dir / relative
    if not path.is_file():
        raise ValueError(f"asset {asset.get('id')} active image is missing: {relative}")
    return path


def _crop_rgb(
    width: int,
    height: int,
    pixels: bytes,
    region: dict[str, Any],
) -> tuple[int, int, bytes]:
    left = max(0, min(width - 1, int(round(float(region["x"]) * width))))
    top = max(0, min(height - 1, int(round(float(region["y"]) * height))))
    right = max(left + 1, min(width, int(round((float(region["x"]) + float(region["width"])) * width))))
    bottom = max(top + 1, min(height, int(round((float(region["y"]) + float(region["height"])) * height))))
    crop_width = right - left
    crop_height = bottom - top
    output = bytearray(crop_width * crop_height * 3)
    for row in range(crop_height):
        source_start = ((top + row) * width + left) * 3
        destination_start = row * crop_width * 3
        output[destination_start:destination_start + crop_width * 3] = pixels[source_start:source_start + crop_width * 3]
    return crop_width, crop_height, bytes(output)


def _contact_sheet_png(sources: list[tuple[int, int, bytes]], *, width: int = 2400) -> bytes:
    if not sources:
        # A valid white placeholder records that a diagnostic kind was not visible;
        # it does not invent or redraw image evidence.
        return _encode_png_rgb(320, 180, bytes([255]) * 320 * 180 * 3)
    columns = min(4, max(1, math.ceil(math.sqrt(len(sources)))))
    rows = math.ceil(len(sources) / columns)
    margin = 24
    cell_width = width // columns
    cell_height = int(cell_width * 9 / 16)
    height = rows * cell_height
    canvas = bytearray([255]) * width * height * 3
    for index, (source_width, source_height, source_pixels) in enumerate(sources):
        fitted_width, fitted_height, fitted = _resize_rgb_nearest(
            source_width,
            source_height,
            source_pixels,
            max(1, cell_width - margin * 2),
            max(1, cell_height - margin * 2),
        )
        column = index % columns
        row = index // columns
        left = column * cell_width + (cell_width - fitted_width) // 2
        top = row * cell_height + (cell_height - fitted_height) // 2
        for fitted_y in range(fitted_height):
            destination = ((top + fitted_y) * width + left) * 3
            source_offset = fitted_y * fitted_width * 3
            canvas[destination:destination + fitted_width * 3] = fitted[source_offset:source_offset + fitted_width * 3]
    return _encode_png_rgb(width, height, bytes(canvas))


def build_review_board(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2
    try:
        _require_schema_16(project_dir)
        assets_manifest = _read_json_strict(project_dir / "manifests/assets.json")
        candidates_manifest = _read_json_strict(project_dir / "manifests/candidates.json")
        reviews_manifest = _read_json_strict(project_dir / "manifests/reviews.json")
        gate = _find_record(reviews_manifest.get("review_gates"), args.gate, "review gate")
        if gate.get("status") not in {"building", "ready_for_review", "changes_requested"}:
            raise ValueError(f"review gate {args.gate} cannot build a board from status={gate.get('status')}")
        assets = {
            item.get("id"): item for item in assets_manifest.get("assets", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        candidate_sets = {
            item.get("id"): item for item in candidates_manifest.get("candidate_sets", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        ordered_assets: list[dict[str, Any]] = []
        selected_regions: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for asset_id in gate.get("asset_ids", []):
            asset = assets.get(asset_id)
            if not isinstance(asset, dict) or asset.get("status") not in {"qualified", "approved"}:
                raise ValueError(f"gate asset {asset_id} must be qualified or approved before board construction")
            candidate_set = candidate_sets.get(asset.get("candidate_set_id"))
            if asset.get("generator") == "builtin-imagegen":
                if not isinstance(candidate_set, dict) or candidate_set.get("status") != "selected":
                    raise ValueError(f"gate asset {asset_id} lacks an internally selected candidate")
                selected_id = candidate_set.get("selected_candidate_id")
                selected = next((item for item in _candidate_variants(candidate_set) if item.get("id") == selected_id), None)
                if not isinstance(selected, dict) or selected.get("quality_verdict") != "pass":
                    raise ValueError(f"gate asset {asset_id} selected candidate has not passed internal QA")
                selected_regions[asset_id] = selected.get("diagnostic_regions", {})
            else:
                selected_regions[asset_id] = {kind: [] for kind in ("face", "hands", "materials", "highlights", "shadows")}
            ordered_assets.append(asset)

        root = Path("assets/review-boards") / f"{args.gate}--v001"
        output_paths = {"overview": root / "overview.png"}
        output_paths.update({kind: root / f"{kind}.png" for kind in ("face", "hands", "materials", "highlights", "shadows")})
        output_paths["map"] = root / "board-map.json"
        if any((project_dir / relative).exists() for relative in output_paths.values()):
            raise ValueError(f"review board {args.gate} v001 already exists; old versions are never overwritten")

        decoded: dict[str, tuple[int, int, bytes]] = {}
        for asset in ordered_assets:
            decoded[str(asset["id"])] = _decode_png_rgb(_active_asset_file(project_dir, asset))
        overview_sources = [decoded[str(asset["id"])] for asset in ordered_assets]
        diagnostic_sources: dict[str, list[tuple[int, int, bytes]]] = {
            kind: [] for kind in ("face", "hands", "materials", "highlights", "shadows")
        }
        map_rows: list[dict[str, Any]] = []
        for asset in ordered_assets:
            asset_id = str(asset["id"])
            width, height, pixels = decoded[asset_id]
            map_rows.append({
                "asset_id": asset_id,
                "source_path": _active_asset_file(project_dir, asset).relative_to(project_dir).as_posix(),
                "source_sha256": _sha256_file(_active_asset_file(project_dir, asset)),
                "diagnostic_regions": selected_regions.get(asset_id, {}),
            })
            for kind, regions in selected_regions.get(asset_id, {}).items():
                if kind not in diagnostic_sources or not isinstance(regions, list):
                    continue
                for region in regions:
                    if isinstance(region, dict):
                        diagnostic_sources[kind].append(_crop_rgb(width, height, pixels, region))

        for relative in output_paths.values():
            (project_dir / relative).parent.mkdir(parents=True, exist_ok=True)
        (project_dir / output_paths["overview"]).write_bytes(_contact_sheet_png(overview_sources))
        for kind, sources in diagnostic_sources.items():
            (project_dir / output_paths[kind]).write_bytes(_contact_sheet_png(sources))
        portable_write_json(
            project_dir / output_paths["map"],
            {
                "schema_version": SCHEMA_VERSION,
                "gate_id": args.gate,
                "layout": "deterministic-original-pixel-contact-and-declared-crops-v1.6",
                "resampling": "nearest-neighbor for display only; source files remain authoritative",
                "inspection_scales": ["thumbnail", "fit", "100%", "200%"],
                "assets": map_rows,
                "files": {key: value.as_posix() for key, value in output_paths.items()},
            },
        )
        gate["review_board_path"] = output_paths["overview"].as_posix()
        gate["diagnostic_board_paths"] = {kind: output_paths[kind].as_posix() for kind in diagnostic_sources}
        gate["status"] = "ready_for_review"
        gate["decision"] = "pending"
        gate["decision_notes"] = []
        gate["decided_at"] = ""
        write_json(project_dir / "manifests/reviews.json", reviews_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: build-review-board failed: {exc}", file=sys.stderr)
        return 2
    print(f"Created gate review board: {project_dir / output_paths['overview']}")
    print("Failed candidates remain hidden; source images were only decoded, cropped and laid out, never regenerated.")
    return 0


__all__ = [name for name in globals() if not name.startswith("__")]
