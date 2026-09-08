"""Deterministic rectangular packing for a small salvage planning problem.

This module deliberately uses only the Python standard library.  It is a
bounded heuristic: it samples a width/depth grid and tries several stable
part orderings with a small backtracking packer.  It does not claim a global
optimum outside those sampled candidates and orderings.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


MAX_BOARDS = 6
MAX_DEFECTS = 8
MAX_CANDIDATES = 1000
# Keep worst-case requests responsive while preserving the explicit public
# contract that no more than MAX_CANDIDATES configurations are considered.
# Ordinary requests (including the demo) remain fully represented; very fine
# grids are sampled to this smaller deterministic working set.
MAX_SEARCH_CANDIDATES = 120
MAX_NEW_BOARDS = 4
MAX_DIMENSION_MM = 1_000_000.0
MAX_KERF_MM = 100.0


class InputError(ValueError):
    """Raised when a planner request cannot be safely normalized."""


def demo_request() -> dict:
    """Return the small deterministic example used by the demo UI."""

    return {
        "design": {
            "width": 600,
            "depth": 240,
            "height": 260,
            "thickness": 18,
            "min_width": 520,
            "min_depth": 200,
            "step": 10,
        },
        "kerf": 3,
        "boards": [
            {
                "id": "cabinet",
                "label": "Cabinet back",
                "width": 590,
                "height": 510,
                "thickness": 18,
                "material": "plywood",
                "grain": "x",
                "defects": [{"x": 565, "y": 0, "width": 25, "height": 510}],
            },
            {
                "id": "shelf",
                "label": "Old shelf",
                "width": 760,
                "height": 260,
                "thickness": 18,
                "material": "plywood",
                "grain": "x",
                "defects": [],
            },
        ],
        "new_stock": {"width": 1220, "height": 610},
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _number(value: Any, name: str, *, minimum: float = 0.0, maximum: float = MAX_DIMENSION_MM) -> float:
    if not _is_number(value):
        raise InputError(f"{name} must be a finite number")
    result = float(value)
    if result < minimum or result > maximum:
        raise InputError(f"{name} must be between {minimum:g} and {maximum:g}")
    return result


def _positive_integerish(value: Any, name: str, *, maximum: int) -> int:
    number = _number(value, name, minimum=1, maximum=maximum)
    if not number.is_integer():
        raise InputError(f"{name} must be an integer")
    return int(number)


def _clean_text(value: Any, name: str, *, default: Optional[str] = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name} must be a non-empty string")
    if len(value.strip()) > 256:
        raise InputError(f"{name} is too long")
    return value.strip()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InputError(f"{name} must be an object")
    return value


def _rect_from(value: Mapping[str, Any], name: str, *, allow_zero: bool = False) -> Dict[str, float]:
    minimum = 0.0 if allow_zero else 0.000001
    return {
        "x": _number(value.get("x"), f"{name}.x", minimum=0.0),
        "y": _number(value.get("y"), f"{name}.y", minimum=0.0),
        "width": _number(value.get("width"), f"{name}.width", minimum=minimum),
        "height": _number(value.get("height"), f"{name}.height", minimum=minimum),
    }


def _round(value: float) -> int | float:
    """Keep JSON output compact while retaining exact integer millimetres."""

    if abs(value - round(value)) < 1e-9:
        return int(round(value))
    return round(value, 6)


def _normal_board(board: Mapping[str, Any], index: int) -> Dict[str, Any]:
    board_name = f"boards[{index}]"
    board_id = _clean_text(board.get("id"), f"{board_name}.id")
    label = _clean_text(board.get("label"), f"{board_name}.label", default=board_id)
    width = _number(board.get("width"), f"{board_name}.width", minimum=0.000001)
    height = _number(board.get("height"), f"{board_name}.height", minimum=0.000001)
    thickness = _number(board.get("thickness"), f"{board_name}.thickness", minimum=0.000001, maximum=1000)
    material = _clean_text(board.get("material"), f"{board_name}.material")
    grain = board.get("grain", "none")
    if grain not in ("x", "none"):
        raise InputError(f"{board_name}.grain must be 'x' or 'none'")
    raw_defects = board.get("defects", [])
    if not isinstance(raw_defects, list):
        raise InputError(f"{board_name}.defects must be an array")
    if len(raw_defects) > MAX_DEFECTS:
        raise InputError(f"{board_name}.defects may contain at most {MAX_DEFECTS} entries")
    defects: List[Dict[str, Any]] = []
    for defect_index, raw_defect in enumerate(raw_defects):
        defect = _rect_from(_mapping(raw_defect, f"{board_name}.defects[{defect_index}]"), f"{board_name}.defects[{defect_index}]")
        if defect["x"] + defect["width"] > width + 1e-9 or defect["y"] + defect["height"] > height + 1e-9:
            raise InputError(f"{board_name}.defects[{defect_index}] must lie inside its board")
        defects.append({key: _round(value) for key, value in defect.items()})
    return {
        "id": board_id,
        "label": label,
        "width": _round(width),
        "height": _round(height),
        "thickness": _round(thickness),
        "material": material,
        "grain": grain,
        "defects": defects,
    }


def _normal_request(request: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(request, Mapping):
        raise InputError("request must be an object")
    design = _mapping(request.get("design"), "design")
    width = _number(design.get("width"), "design.width", minimum=0.000001)
    depth = _number(design.get("depth"), "design.depth", minimum=0.000001)
    height = _number(design.get("height"), "design.height", minimum=0.000001)
    thickness = _number(design.get("thickness"), "design.thickness", minimum=0.000001, maximum=1000)
    min_width = _number(design.get("min_width", width), "design.min_width", minimum=0.000001)
    min_depth = _number(design.get("min_depth", depth), "design.min_depth", minimum=0.000001)
    step = _number(design.get("step", 10), "design.step", minimum=0.000001, maximum=MAX_DIMENSION_MM)
    if min_width > width or min_depth > depth:
        raise InputError("minimum design dimensions cannot exceed target dimensions")
    if width <= 3.0 * thickness or min_width <= 3.0 * thickness:
        raise InputError("design width and minimum width must exceed three times thickness")
    kerf = _number(request.get("kerf", 0), "kerf", minimum=0, maximum=MAX_KERF_MM)
    raw_boards = request.get("boards", [])
    if not isinstance(raw_boards, list):
        raise InputError("boards must be an array")
    if len(raw_boards) > MAX_BOARDS:
        raise InputError(f"boards may contain at most {MAX_BOARDS} entries")
    boards = [_normal_board(_mapping(board, f"boards[{index}]"), index) for index, board in enumerate(raw_boards)]
    board_ids = [board["id"] for board in boards]
    if len(set(board_ids)) != len(board_ids):
        raise InputError("board ids must be unique")
    if boards:
        materials = {board["material"] for board in boards}
        thicknesses = {float(board["thickness"]) for board in boards}
        if len(materials) != 1:
            raise InputError("all boards must use the same material")
        if any(abs(thickness_value - thickness) > 1e-9 for thickness_value in thicknesses):
            raise InputError("all board thicknesses must match design.thickness")
        material = next(iter(materials))
    else:
        material = "salvaged-material"
    raw_new = request.get("new_stock")
    new_stock = None
    if raw_new is not None:
        new_mapping = _mapping(raw_new, "new_stock")
        new_stock = {
            "width": _round(_number(new_mapping.get("width"), "new_stock.width", minimum=0.000001)),
            "height": _round(_number(new_mapping.get("height"), "new_stock.height", minimum=0.000001)),
        }
        if "thickness" in new_mapping:
            new_thickness = _number(new_mapping.get("thickness"), "new_stock.thickness", minimum=0.000001, maximum=1000)
            if abs(new_thickness - thickness) > 1e-9:
                raise InputError("new_stock.thickness must match design.thickness")
        new_material = new_mapping.get("material", material)
        if not isinstance(new_material, str) or not new_material.strip():
            raise InputError("new_stock.material must be a non-empty string")
        if len(new_material.strip()) > 256:
            raise InputError("new_stock.material is too long")
        if new_material.strip() != material:
            raise InputError("new_stock.material must match salvage material")
        new_stock["thickness"] = _round(thickness)
        new_stock["material"] = material
    normalized_design = {
        "width": _round(width),
        "depth": _round(depth),
        "height": _round(height),
        "thickness": _round(thickness),
        "min_width": _round(min_width),
        "min_depth": _round(min_depth),
        "step": _round(step),
    }
    # Rebuild in a stable, explicit order and ignore UI-only request extras.
    normalized: Dict[str, Any] = {
        "design": normalized_design,
        "kerf": _round(kerf),
        "boards": boards,
    }
    if new_stock is not None:
        normalized["new_stock"] = new_stock
    return normalized


def _grid_values(target: float, minimum: float, step: float) -> List[float]:
    values: List[float] = []
    current = target
    # The epsilon prevents a tiny floating point tail from adding one value.
    while current >= minimum - 1e-9:
        values.append(_round(current))
        current -= step
        if len(values) > MAX_CANDIDATES * 4:
            break
    if not values or abs(float(values[-1]) - minimum) > 1e-7:
        values.append(_round(minimum))
    # Dedupe after rounding and preserve descending order.
    result: List[float] = []
    for value in values:
        if not result or abs(float(result[-1]) - float(value)) > 1e-9:
            result.append(float(value))
    return result


def _sample_candidates(design: Mapping[str, Any]) -> List[Tuple[float, float]]:
    widths = _grid_values(float(design["width"]), float(design["min_width"]), float(design["step"]))
    depths = _grid_values(float(design["depth"]), float(design["min_depth"]), float(design["step"]))
    total = len(widths) * len(depths)
    if total <= MAX_SEARCH_CANDIDATES:
        return [(width, depth) for width in widths for depth in depths]
    # Keep target/minimum corners and then deterministic evenly spaced entries.
    corners = [(widths[0], depths[0]), (widths[0], depths[-1]), (widths[-1], depths[0]), (widths[-1], depths[-1])]
    selected = []
    for pair in corners:
        if pair not in selected:
            selected.append(pair)
    slots = MAX_SEARCH_CANDIDATES - len(selected)
    if slots <= 0:
        return selected[:MAX_SEARCH_CANDIDATES]
    # Enumerate product indices directly.  This avoids materializing millions
    # of tuples for a request with a fine step.
    selected_set = set(selected)
    for index in range(slots):
        flat_index = int(index * total / slots)
        width_index, depth_index = divmod(flat_index, len(depths))
        pair = (widths[width_index], depths[depth_index])
        if pair in selected_set:
            continue
        selected.append(pair)
        selected_set.add(pair)
    return selected[:MAX_SEARCH_CANDIDATES]


def _part_list(design: Mapping[str, Any], material: str) -> List[Dict[str, Any]]:
    width = float(design["width"])
    depth = float(design["depth"])
    inner_height = float(design["height"]) - 2.0 * float(design["thickness"])
    if inner_height <= 0:
        raise InputError("design.height must exceed twice design.thickness")
    thickness = float(design["thickness"])
    return [
        {"id": "top", "label": "Top", "width": _round(width), "height": _round(depth), "thickness": _round(thickness), "material": material, "grain": "x"},
        {"id": "base", "label": "Base", "width": _round(width), "height": _round(depth), "thickness": _round(thickness), "material": material, "grain": "x"},
        {"id": "side-1", "label": "Side 1", "width": _round(inner_height), "height": _round(depth), "thickness": _round(thickness), "material": material, "grain": "x"},
        {"id": "side-2", "label": "Side 2", "width": _round(inner_height), "height": _round(depth), "thickness": _round(thickness), "material": material, "grain": "x"},
        {"id": "divider", "label": "Divider", "width": _round(inner_height), "height": _round(depth), "thickness": _round(thickness), "material": material, "grain": "x"},
    ]


def _new_boards(stock: Optional[Mapping[str, Any]], thickness: float, material: str, count: int = MAX_NEW_BOARDS, existing_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    if stock is None:
        return []
    occupied = set(existing_ids or ())
    result = []
    index = 1
    while len(result) < count:
        board_id = f"new-{index}"
        index += 1
        if board_id in occupied:
            continue
        result.append({
            "id": board_id,
            "label": f"New panel {len(result) + 1}",
            "width": stock["width"],
            "height": stock["height"],
            "thickness": _round(thickness),
            "material": material,
            "grain": "none",
            "defects": [],
            "new": True,
        })
        occupied.add(board_id)
    return result


def _dims(obj: Mapping[str, Any], width_name: str = "width", height_name: str = "height") -> Tuple[float, float]:
    return float(obj[width_name]), float(obj[height_name])


def _expanded(rect: Mapping[str, Any], margin: float) -> Tuple[float, float, float, float]:
    return (
        float(rect["x"]) - margin,
        float(rect["y"]) - margin,
        float(rect["x"]) + float(rect["width"]) + margin,
        float(rect["y"]) + float(rect["height"]) + margin,
    )


def _intersects(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], epsilon: float = 1e-9) -> bool:
    return a[0] < b[2] - epsilon and a[2] > b[0] + epsilon and a[1] < b[3] - epsilon and a[3] > b[1] + epsilon


def _gap_at_least(a: Mapping[str, Any], b: Mapping[str, Any], kerf: float) -> bool:
    # Expand both cuts by half the requested kerf.  This catches overlap,
    # edge contact, and diagonal corner gaps smaller than kerf while allowing
    # two rectangles to be close when they are separated along both axes.
    return not _intersects(_expanded(a, kerf / 2.0), _expanded(b, kerf / 2.0))


def _placement_rect(x: float, y: float, width: float, height: float) -> Dict[str, float]:
    return {"x": x, "y": y, "width": width, "height": height}


def _position_candidates(board: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], part_width: float, part_height: float, kerf: float) -> List[Tuple[float, float]]:
    board_width = float(board["width"])
    board_height = float(board["height"])
    if part_width > board_width + 1e-9 or part_height > board_height + 1e-9:
        return []
    xs = {0.0, max(0.0, board_width - part_width)}
    ys = {0.0, max(0.0, board_height - part_height)}
    for existing in placed:
        ex = float(existing["x"])
        ey = float(existing["y"])
        ew = float(existing["width"])
        eh = float(existing["height"])
        xs.update((ex + ew + kerf, ex - part_width - kerf, ex + ew, ex - part_width))
        ys.update((ey + eh + kerf, ey - part_height - kerf, ey + eh, ey - part_height))
    for defect in board.get("defects", []):
        dx = float(defect["x"])
        dy = float(defect["y"])
        dw = float(defect["width"])
        dh = float(defect["height"])
        margin = kerf / 2.0
        xs.update((dx + dw + margin, dx - part_width - margin))
        ys.update((dy + dh + margin, dy - part_height - margin))
    valid = []
    for x in xs:
        for y in ys:
            if x >= -1e-9 and y >= -1e-9 and x + part_width <= board_width + 1e-9 and y + part_height <= board_height + 1e-9:
                valid.append((max(0.0, x), max(0.0, y)))
    return sorted(set(valid), key=lambda point: (point[1], point[0]))


def _can_place(board: Mapping[str, Any], rect: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], kerf: float) -> bool:
    bx = float(board["width"])
    by = float(board["height"])
    x, y, width, height = (float(rect[key]) for key in ("x", "y", "width", "height"))
    if x < -1e-9 or y < -1e-9 or x + width > bx + 1e-9 or y + height > by + 1e-9:
        return False
    placement_box = _expanded(rect, kerf / 2.0)
    for defect in board.get("defects", []):
        defect_box = (float(defect["x"]), float(defect["y"]), float(defect["x"]) + float(defect["width"]), float(defect["y"]) + float(defect["height"]))
        if _intersects(placement_box, defect_box):
            return False
    for existing in placed:
        if not _gap_at_least(rect, existing, kerf):
            return False
    return True


def _part_orientations(part: Mapping[str, Any], board: Mapping[str, Any]) -> List[Tuple[float, float, bool]]:
    width = float(part["width"])
    height = float(part["height"])
    result = [(width, height, False)]
    if board.get("grain", "none") == "none" and abs(width - height) > 1e-9:
        result.append((height, width, True))
    return result


def _ordering_variants(parts: Sequence[Mapping[str, Any]]) -> List[List[Mapping[str, Any]]]:
    variants: List[List[Mapping[str, Any]]] = []
    keys = [
        lambda p: (-float(p["width"]) * float(p["height"]), -float(p["width"]), p["id"]),
        lambda p: (-max(float(p["width"]), float(p["height"])), -min(float(p["width"]), float(p["height"])), p["id"]),
        lambda p: (-float(p["height"]), -float(p["width"]), p["id"]),
        lambda p: (-float(p["width"]), -float(p["height"]), p["id"]),
        lambda p: (p["id"],),
    ]
    for key in keys:
        ordered = sorted(parts, key=key)
        if [part["id"] for part in ordered] not in [[part["id"] for part in prior] for prior in variants]:
            variants.append(ordered)
    return variants


def _pack(parts: Sequence[Mapping[str, Any]], boards: Sequence[Mapping[str, Any]], kerf: float) -> Optional[Dict[str, Any]]:
    if not parts:
        return {"placements": [], "used_board_ids": [], "board_count": 0}
    best: Optional[Dict[str, Any]] = None
    # Recursive search is bounded by the tiny five-part workflow.  A node cap
    # prevents malformed future workflows from turning this into an unbounded
    # solver while retaining all practical layouts here.
    node_cap = 250
    for ordered_parts in _ordering_variants(parts):
        nodes = [0]
        placements: List[Dict[str, Any]] = []
        found_this_order = [False]

        def visit(index: int) -> None:
            nonlocal best
            if found_this_order[0]:
                return
            nodes[0] += 1
            if nodes[0] > node_cap:
                return
            if index >= len(ordered_parts):
                used = sorted({placement["board_id"] for placement in placements})
                area = sum(float(placement["width"]) * float(placement["height"]) for placement in placements)
                board_waste = sum(float(board["width"]) * float(board["height"]) for board in boards if board["id"] in used) - area
                score = (len(used), board_waste, tuple((item["board_id"], item["y"], item["x"], item["part_id"]) for item in placements))
                if best is None or score < best["score"]:
                    best = {"placements": deepcopy(placements), "used_board_ids": used, "board_count": len(used), "score": score}
                found_this_order[0] = True
                return
            part = ordered_parts[index]
            # Prefer boards in input order, and then bottom-left positions.
            for board in boards:
                board_placed = [placement for placement in placements if placement["board_id"] == board["id"]]
                for width, height, rotated in _part_orientations(part, board):
                    for x, y in _position_candidates(board, board_placed, width, height, kerf):
                        rect = _placement_rect(x, y, width, height)
                        if not _can_place(board, rect, board_placed, kerf):
                            continue
                        placement = {
                            "part_id": part["id"],
                            "board_id": board["id"],
                            "x": _round(x),
                            "y": _round(y),
                            "width": _round(width),
                            "height": _round(height),
                            "rotated": bool(rotated),
                        }
                        placements.append(placement)
                        visit(index + 1)
                        placements.pop()
                        if found_this_order[0]:
                            return

        visit(0)
    return best


def _plan_summary(plan: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not plan:
        return {"status": "no_fit", "board_count": 0, "new_board_count": 0, "placements": []}
    return {
        "status": "feasible",
        "board_count": int(plan["board_count"]),
        "new_board_count": int(plan.get("new_board_count", 0)),
        "placements": deepcopy(plan["placements"]),
    }


def _used_board_area(boards: Sequence[Mapping[str, Any]], placements: Sequence[Mapping[str, Any]]) -> float:
    ids = {placement.get("board_id") for placement in placements}
    return sum(float(board["width"]) * float(board["height"]) for board in boards if board.get("id") in ids)


def _serialize_design(width: float, depth: float, design: Mapping[str, Any], score: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "width_mm": _round(width),
        "depth_mm": _round(depth),
        "height_mm": design["height"],
        "thickness_mm": design["thickness"],
    }
    if score is not None:
        result["score"] = dict(score)
    return result


def _serialize_part(part: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": part["id"],
        "label": part["label"],
        "width_mm": part["width"],
        "height_mm": part["height"],
        "thickness_mm": part["thickness"],
        "material": part["material"],
        "grain": part["grain"],
    }


def _fingerprint(request: Mapping[str, Any]) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_plan(boards: Sequence[Mapping[str, Any]], parts: Sequence[Mapping[str, Any]], placements: Sequence[Mapping[str, Any]], kerf: Any) -> Dict[str, Any]:
    """Validate a plan independently of candidate search.

    The return shape remains useful to callers even for malformed plans; all
    failures are collected in ``errors`` rather than causing a partial pass.
    """

    errors: List[str] = []
    checks: Dict[str, bool] = {
        "inputs": True,
        "references": True,
        "bounds": True,
        "defects": True,
        "overlap_kerf": True,
        "grain": True,
        "dimensions": True,
        "material": True,
        "complete": True,
    }
    try:
        if not isinstance(boards, Sequence) or isinstance(boards, (str, bytes)):
            raise ValueError("boards must be an array")
        if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)):
            raise ValueError("parts must be an array")
        if not isinstance(placements, Sequence) or isinstance(placements, (str, bytes)):
            raise ValueError("placements must be an array")
        if len(boards) > 10 or len(parts) > 5 or len(placements) > 5:
            raise ValueError("geometry verification allows at most 10 boards, 5 parts and 5 placements")
        if not _is_number(kerf) or float(kerf) < 0 or float(kerf) > MAX_KERF_MM:
            raise ValueError("kerf must be a finite number between 0 and 100")
        kerf_value = float(kerf)
    except ValueError as exc:
        checks["inputs"] = False
        errors.append(str(exc))
        return {"valid": False, "checks": checks, "errors": errors}

    board_by_id: Dict[str, Mapping[str, Any]] = {}
    part_by_id: Dict[str, Mapping[str, Any]] = {}
    for index, board in enumerate(boards):
        if not isinstance(board, Mapping):
            checks["inputs"] = False
            errors.append(f"board {index} must be an object")
            continue
        board_id = board.get("id")
        if not isinstance(board_id, str) or not board_id:
            checks["inputs"] = False
            errors.append(f"board {index} has invalid id")
            continue
        if board_id in board_by_id:
            checks["inputs"] = False
            errors.append(f"duplicate board id {board_id}")
        board_by_id[board_id] = board
        try:
            if isinstance(board.get("width"), bool) or isinstance(board.get("height"), bool):
                raise ValueError
            board_width = float(board.get("width"))
            board_height = float(board.get("height"))
            if not math.isfinite(board_width) or not math.isfinite(board_height) or board_width <= 0 or board_height <= 0:
                raise ValueError
        except (TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"board {board_id} has invalid dimensions")
            board_width = board_height = 0.0
        try:
            if isinstance(board.get("thickness"), bool):
                raise ValueError
            board_thickness = float(board.get("thickness"))
            if not math.isfinite(board_thickness) or board_thickness <= 0:
                raise ValueError
        except (TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"board {board_id} has invalid thickness")
        if not isinstance(board.get("material"), str) or not board.get("material", "").strip():
            checks["inputs"] = False
            errors.append(f"board {board_id} has invalid material")
        if board.get("grain", "none") not in ("x", "none"):
            checks["inputs"] = False
            errors.append(f"board {board_id} has invalid grain")
        raw_defects = board.get("defects", [])
        if not isinstance(raw_defects, Sequence) or isinstance(raw_defects, (str, bytes)):
            checks["inputs"] = False
            errors.append(f"board {board_id} defects must be an array")
        elif len(raw_defects) > MAX_DEFECTS:
            checks["inputs"] = False
            errors.append(f"board {board_id} has too many defects")
        else:
            for defect_index, defect in enumerate(raw_defects):
                if not isinstance(defect, Mapping):
                    checks["inputs"] = False
                    errors.append(f"board {board_id} defect {defect_index} must be an object")
                    continue
                try:
                    if any(isinstance(defect.get(key), bool) for key in ("x", "y", "width", "height")):
                        raise ValueError
                    defect_values = tuple(float(defect[key]) for key in ("x", "y", "width", "height"))
                    if not all(math.isfinite(value) for value in defect_values) or defect_values[0] < 0 or defect_values[1] < 0 or defect_values[2] <= 0 or defect_values[3] <= 0 or defect_values[0] + defect_values[2] > board_width + 1e-9 or defect_values[1] + defect_values[3] > board_height + 1e-9:
                        raise ValueError
                except (KeyError, TypeError, ValueError):
                    checks["inputs"] = False
                    errors.append(f"board {board_id} defect {defect_index} has invalid bounds")
    for index, part in enumerate(parts):
        if not isinstance(part, Mapping):
            checks["inputs"] = False
            errors.append(f"part {index} must be an object")
            continue
        part_id = part.get("id", part.get("part_id"))
        if not isinstance(part_id, str) or not part_id:
            checks["inputs"] = False
            errors.append(f"part {index} has invalid id")
            continue
        if part_id in part_by_id:
            checks["inputs"] = False
            errors.append(f"duplicate part id {part_id}")
        part_by_id[part_id] = part
        try:
            if isinstance(part.get("width", part.get("width_mm")), bool) or isinstance(part.get("height", part.get("height_mm")), bool):
                raise ValueError
            part_width = float(part.get("width", part.get("width_mm")))
            part_height = float(part.get("height", part.get("height_mm")))
            if not math.isfinite(part_width) or not math.isfinite(part_height) or part_width <= 0 or part_height <= 0:
                raise ValueError
        except (TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"part {part_id} has invalid dimensions")
        try:
            if isinstance(part.get("thickness", part.get("thickness_mm")), bool):
                raise ValueError
            part_thickness = float(part.get("thickness", part.get("thickness_mm")))
            if not math.isfinite(part_thickness) or part_thickness <= 0:
                raise ValueError
        except (TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"part {part_id} has invalid thickness")
        if not isinstance(part.get("material"), str) or not part.get("material", "").strip():
            checks["inputs"] = False
            errors.append(f"part {part_id} has invalid material")
        if part.get("grain", "x") not in ("x", "none"):
            checks["inputs"] = False
            errors.append(f"part {part_id} has invalid grain")

    seen_parts: Dict[str, int] = {}
    placement_by_board: Dict[str, List[Mapping[str, Any]]] = {}
    for index, placement in enumerate(placements):
        prefix = f"placement {index}"
        if not isinstance(placement, Mapping):
            checks["inputs"] = False
            errors.append(f"{prefix} must be an object")
            continue
        board_id = placement.get("board_id")
        part_id = placement.get("part_id")
        board = board_by_id.get(board_id) if isinstance(board_id, str) else None
        part = part_by_id.get(part_id) if isinstance(part_id, str) else None
        if board is None:
            checks["references"] = False
            errors.append(f"{prefix} references unknown board {board_id!r}")
            continue
        if part is None:
            checks["references"] = False
            errors.append(f"{prefix} references unknown part {part_id!r}")
            continue
        seen_parts[str(part_id)] = seen_parts.get(str(part_id), 0) + 1
        placement_by_board.setdefault(str(board_id), []).append(placement)
        if not isinstance(placement.get("rotated", False), bool):
            checks["inputs"] = False
            errors.append(f"{prefix}.rotated must be boolean")
        try:
            x = float(placement["x"])
            y = float(placement["y"])
            width = float(placement["width"])
            height = float(placement["height"])
            if any(isinstance(placement[key], bool) for key in ("x", "y", "width", "height")):
                raise ValueError
            if not all(math.isfinite(value) for value in (x, y, width, height)) or width <= 0 or height <= 0:
                raise ValueError("non-positive or non-finite geometry")
        except (KeyError, TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"{prefix} has invalid geometry")
            continue
        try:
            board_width = float(board.get("width", 0))
            board_height = float(board.get("height", 0))
            if isinstance(board.get("width", 0), bool) or isinstance(board.get("height", 0), bool):
                raise ValueError
        except (TypeError, ValueError):
            board_width = board_height = 0.0
        if not math.isfinite(board_width) or not math.isfinite(board_height):
            board_width = board_height = 0.0
        if x < -1e-9 or y < -1e-9 or x + width > board_width + 1e-9 or y + height > board_height + 1e-9:
            checks["bounds"] = False
            errors.append(f"{prefix} is outside board bounds")
        defects = board.get("defects", [])
        if not isinstance(defects, Sequence) or isinstance(defects, (str, bytes)):
            checks["inputs"] = False
            errors.append(f"board {board_id} defects must be an array")
            defects = []
        box = _expanded({"x": x, "y": y, "width": width, "height": height}, kerf_value / 2.0)
        for defect in defects:
            if not isinstance(defect, Mapping):
                checks["inputs"] = False
                errors.append(f"board {board_id} contains malformed defect")
                continue
            try:
                if any(isinstance(defect.get(key), bool) for key in ("x", "y", "width", "height")):
                    raise ValueError
                defect_values = tuple(float(defect[key]) for key in ("x", "y", "width", "height"))
                if not all(math.isfinite(value) for value in defect_values) or defect_values[2] <= 0 or defect_values[3] <= 0:
                    raise ValueError
                defect_box = (defect_values[0], defect_values[1], defect_values[0] + defect_values[2], defect_values[1] + defect_values[3])
            except (KeyError, TypeError, ValueError):
                checks["inputs"] = False
                errors.append(f"board {board_id} contains malformed defect")
                continue
            if _intersects(box, defect_box):
                checks["defects"] = False
                errors.append(f"{prefix} intersects a defect with kerf safety")
                break
        try:
            if isinstance(part.get("width", part.get("width_mm", 0)), bool) or isinstance(part.get("height", part.get("height_mm", 0)), bool):
                raise ValueError
            part_width = float(part.get("width", part.get("width_mm", 0)))
            part_height = float(part.get("height", part.get("height_mm", 0)))
            if not math.isfinite(part_width) or not math.isfinite(part_height) or part_width <= 0 or part_height <= 0:
                raise ValueError
        except (TypeError, ValueError):
            checks["inputs"] = False
            errors.append(f"part {part_id} has invalid dimensions")
            part_width = part_height = 0.0
        rotated = placement.get("rotated", False) if isinstance(placement.get("rotated", False), bool) else False
        expected_width, expected_height = (part_height, part_width) if rotated else (part_width, part_height)
        if abs(width - expected_width) > 1e-7 or abs(height - expected_height) > 1e-7:
            checks["dimensions"] = False
            errors.append(f"{prefix} dimensions do not match part orientation")
        if board.get("grain", "none") == "x" and rotated:
            checks["grain"] = False
            errors.append(f"{prefix} rotates a grain-aligned board")
        part_grain = part.get("grain", "x")
        if part_grain not in ("x", "none"):
            checks["grain"] = False
            errors.append(f"{prefix} has incompatible part grain")
        if ("thickness" in board or "thickness_mm" in board) and ("thickness" in part or "thickness_mm" in part):
            try:
                if isinstance(board.get("thickness", board.get("thickness_mm")), bool) or isinstance(part.get("thickness", part.get("thickness_mm")), bool):
                    raise ValueError
                board_thickness = float(board.get("thickness", board.get("thickness_mm")))
                part_thickness = float(part.get("thickness", part.get("thickness_mm")))
                if abs(board_thickness - part_thickness) > 1e-7:
                    checks["material"] = False
                    errors.append(f"{prefix} thickness does not match board")
            except (TypeError, ValueError):
                checks["material"] = False
                errors.append(f"{prefix} has invalid thickness")
        if "material" in board and "material" in part and board["material"] != part["material"]:
            checks["material"] = False
            errors.append(f"{prefix} material does not match board")

    expected_ids = set(part_by_id)
    if set(seen_parts) != expected_ids or any(count != 1 for count in seen_parts.values()):
        checks["complete"] = False
        missing = sorted(expected_ids - set(seen_parts))
        duplicate = sorted(part_id for part_id, count in seen_parts.items() if count > 1)
        if missing:
            errors.append(f"missing parts: {', '.join(missing)}")
        if duplicate:
            errors.append(f"parts placed more than once: {', '.join(duplicate)}")
    for board_id, board_placements in placement_by_board.items():
        for left_index in range(len(board_placements)):
            left = board_placements[left_index]
            for right in board_placements[left_index + 1 :]:
                try:
                    if not _gap_at_least(left, right, kerf_value):
                        checks["overlap_kerf"] = False
                        errors.append(f"placements on board {board_id} overlap or lack kerf spacing")
                except (KeyError, TypeError, ValueError):
                    checks["inputs"] = False
    board_materials = {board.get("material") for board in board_by_id.values() if isinstance(board.get("material"), str)}
    part_materials = {part.get("material") for part in part_by_id.values() if isinstance(part.get("material"), str)}
    if len(board_materials) > 1 or len(part_materials) > 1:
        checks["material"] = False
        errors.append("all boards and parts must use one material")
    try:
        board_thicknesses = {float(board.get("thickness", board.get("thickness_mm"))) for board in board_by_id.values()}
        part_thicknesses = {float(part.get("thickness", part.get("thickness_mm"))) for part in part_by_id.values()}
        if len(board_thicknesses) > 1 or len(part_thicknesses) > 1:
            checks["material"] = False
            errors.append("all boards and parts must use one thickness")
    except (TypeError, ValueError):
        checks["inputs"] = False
    valid = not errors and all(checks.values())
    return {"valid": valid, "checks": checks, "errors": errors}


def solve(request: dict) -> dict:
    """Solve a bounded inverse-salvage plan and return a JSON-ready object."""

    normalized_request = _normal_request(request)
    design = normalized_request["design"]
    kerf = float(normalized_request["kerf"])
    inventory = normalized_request["boards"]
    material = inventory[0]["material"] if inventory else "salvaged-material"
    candidate_pairs = _sample_candidates(design)
    candidates: List[Dict[str, Any]] = []
    feasible_candidates: List[Dict[str, Any]] = []
    for width, depth in candidate_pairs:
        candidate_design = dict(design)
        candidate_design["width"] = _round(width)
        candidate_design["depth"] = _round(depth)
        parts = _part_list(candidate_design, material)
        plan = _pack(parts, inventory, kerf)
        if plan:
            # The validator is the independent acceptance gate.
            certificate = validate_plan(inventory, parts, plan["placements"], kerf)
            if not certificate["valid"]:
                plan = None
        loss_width = (float(design["width"]) - width) / float(design["width"])
        loss_depth = (float(design["depth"]) - depth) / float(design["depth"])
        area = width * depth
        record = {
            "width_mm": _round(width),
            "depth_mm": _round(depth),
            "feasible": bool(plan),
            "width_loss_normalized": round(loss_width, 9),
            "depth_loss_normalized": round(loss_depth, 9),
            "area_mm2": _round(area),
        }
        candidates.append(record)
        if plan:
            score = (loss_width + loss_depth, -area, -width, -depth)
            feasible_candidates.append({"width": width, "depth": depth, "plan": plan, "score": score, "record": record})

    feasible_candidates.sort(key=lambda item: item["score"])
    selected = feasible_candidates[0] if feasible_candidates else None
    selected_design = None
    selected_parts: List[Dict[str, Any]] = []
    selected_placements: List[Dict[str, Any]] = []
    selected_certificate: Dict[str, Any]
    if selected:
        selected_design = _serialize_design(
            selected["width"],
            selected["depth"],
            design,
            {
                "normalized_width_loss": round((float(design["width"]) - selected["width"]) / float(design["width"]), 9),
                "normalized_depth_loss": round((float(design["depth"]) - selected["depth"]) / float(design["depth"]), 9),
                "combined_normalized_loss": round(selected["score"][0], 9),
                "area_mm2": _round(selected["width"] * selected["depth"]),
            },
        )
        selected_parts_raw = _part_list({**design, "width": selected["width"], "depth": selected["depth"]}, material)
        selected_parts = [_serialize_part(part) for part in selected_parts_raw]
        selected_placements = deepcopy(selected["plan"]["placements"])
        selected_certificate = validate_plan(inventory, selected_parts_raw, selected_placements, kerf)
    else:
        # Keep the certificate useful on no-fit responses: it reports the
        # expected parts as missing, rather than pretending an empty plan is a
        # valid design.
        selected_parts_raw = _part_list(design, material)
        selected_parts = [_serialize_part(part) for part in selected_parts_raw]
        selected_certificate = validate_plan(inventory, selected_parts_raw, [], kerf)

    # The baseline is always the fixed target and can consume at most four
    # identical new panels.  Count new panels used by a heuristic result; this
    # is deliberately labelled as non-minimal in the response.
    target_parts_raw = _part_list(design, material)
    baseline_boards = list(inventory) + _new_boards(normalized_request.get("new_stock"), float(design["thickness"]), material, existing_ids={board["id"] for board in inventory})
    baseline_plan = _pack(target_parts_raw, baseline_boards, kerf)
    if baseline_plan:
        baseline_plan["new_board_count"] = sum(1 for board_id in baseline_plan["used_board_ids"] if str(board_id).startswith("new-"))
        baseline_certificate = validate_plan(baseline_boards, target_parts_raw, baseline_plan["placements"], kerf)
        if not baseline_certificate["valid"]:
            baseline_plan = None
    baseline_placements = deepcopy(baseline_plan["placements"]) if baseline_plan else []
    baseline_used_boards = [board for board in baseline_boards if board["id"] in {p["board_id"] for p in baseline_placements}]
    baseline_new_count = sum(1 for board in baseline_used_boards if board.get("new"))
    baseline: Dict[str, Any] = {
        "design": "fixed target",
        "status": "feasible" if baseline_plan else "no_fit",
        "new_boards": baseline_new_count if baseline_plan else None,
        "purchased_area_mm2": _round(baseline_new_count * float(normalized_request.get("new_stock", {}).get("width", 0)) * float(normalized_request.get("new_stock", {}).get("height", 0))) if baseline_plan else 0,
        "minimum_proven": False,
        "placements": baseline_placements,
        "boards": deepcopy(baseline_used_boards),
        "certificate": baseline_certificate if baseline_plan else validate_plan(baseline_boards, target_parts_raw, [], kerf),
        "explanation": "new_boards is the count used by this deterministic packing heuristic; it is not a proven minimum",
    }
    # Optional no-salvage equivalent, useful for communicating the baseline's
    # value without affecting the salvage-only selection.
    new_only_boards = _new_boards(normalized_request.get("new_stock"), float(design["thickness"]), material)
    no_salvage_plan = _pack(target_parts_raw, new_only_boards, kerf)
    if no_salvage_plan:
        no_salvage_plan["new_board_count"] = len(no_salvage_plan["used_board_ids"])
    baseline["no_salvage"] = {
        "status": "feasible" if no_salvage_plan else "no_fit",
        "new_boards": len(no_salvage_plan["used_board_ids"]) if no_salvage_plan else None,
        "placements": deepcopy(no_salvage_plan["placements"]) if no_salvage_plan else [],
    }

    selected_used_board_ids = {placement["board_id"] for placement in selected_placements}
    selected_boards = [deepcopy(board) for board in inventory if board["id"] in selected_used_board_ids]
    selected_board_area = _used_board_area(inventory, selected_placements)
    selected_material_area = sum(float(part["width"]) * float(part["height"]) for part in selected_parts_raw) if selected else 0.0
    selected_target_area = float(design["width"]) * float(design["depth"])
    selected_area = float(selected["width"]) * float(selected["depth"]) if selected else 0.0
    alternatives: List[Dict[str, Any]] = []
    for alternative in feasible_candidates[1:7]:
        alternatives.append({
            "design": _serialize_design(alternative["width"], alternative["depth"], design),
            "board_count": alternative["plan"]["board_count"],
            "new_board_count": 0,
            "placements": deepcopy(alternative["plan"]["placements"]),
        })
    explanation = [
        "Candidates are sampled on the requested descending width/depth grid.",
        "The selected design minimizes combined normalized width/depth sacrifice, then maximizes area.",
        "Packing uses deterministic bottom-left edge candidates with several part orderings.",
    ]
    if selected:
        explanation.append(f"Salvage-only packing is feasible at {selected_design['width_mm']} x {selected_design['depth_mm']} mm.")
    else:
        explanation.append("No sampled design fits using salvage-only boards within the requested minimum dimensions.")
    caveats = [
        "This is a bounded heuristic over the sampled grid; feasibility and closest-design ranking are not global optimality proofs.",
        "Kerf is modeled as a minimum gap between cuts and a half-kerf defect safety margin.",
    ]
    return {
        "status": "feasible" if selected else "no_fit",
        "request": deepcopy(normalized_request),
        "input_fingerprint": _fingerprint(normalized_request),
        "target": {
            "width_mm": design["width"],
            "depth_mm": design["depth"],
            "height_mm": design["height"],
            "thickness_mm": design["thickness"],
        },
        "selected_design": selected_design,
        "parts": selected_parts,
        "placements": selected_placements,
        "boards": selected_boards,
        "search": {
            "candidates": len(candidates),
            "feasible": len(feasible_candidates),
            "grid": {
                "target_width_mm": design["width"],
                "target_depth_mm": design["depth"],
                "min_width_mm": design["min_width"],
                "min_depth_mm": design["min_depth"],
                "step_mm": design["step"],
            },
            "selection": "closest sampled feasible design",
            "global_optimum_proven": False,
            "candidate_records": candidates,
        },
        "metrics": {
            "target_area_mm2": _round(selected_target_area),
            "selected_area_mm2": _round(selected_area),
            "material_area_mm2": _round(selected_material_area),
            "used_board_area_mm2": _round(selected_board_area),
            "residual_area_mm2": _round(max(0.0, selected_board_area - selected_material_area)),
            "board_count": len(selected_boards),
            "new_board_count": 0,
        },
        "baseline": baseline,
        "certificate": selected_certificate,
        "alternatives": alternatives,
        "explanations": explanation,
        "caveats": caveats,
    }
