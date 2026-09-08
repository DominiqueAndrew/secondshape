import copy
import json
import math
import pathlib
import sys

import pytest


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from secondshape import demo_request, solve, validate_plan


def test_demo_finds_salvage_width560_and_certificate():
    result = solve(demo_request())
    assert result["status"] == "feasible"
    assert result["selected_design"]["width_mm"] == 560
    assert result["selected_design"]["depth_mm"] == 240
    assert len(result["placements"]) == 5
    assert result["certificate"]["valid"] is True
    assert result["baseline"]["status"] == "feasible"
    assert result["baseline"]["new_boards"] >= 1
    assert result["baseline"]["minimum_proven"] is False


def test_changed_defect_invalidates_previous_plan():
    request = demo_request()
    first = solve(request)
    changed = copy.deepcopy(request)
    changed["boards"][1]["defects"] = [{"x": 0, "y": 0, "width": 760, "height": 260}]
    second = solve(changed)
    assert first["certificate"]["valid"]
    assert second["status"] == "no_fit"


def test_validator_catches_overlap_kerf_grain_and_out_of_bounds():
    board = {"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "x", "defects": []}
    parts = [
        {"id": "a", "width": 40, "height": 20, "thickness": 18, "material": "p", "grain": "x"},
        {"id": "b", "width": 40, "height": 20, "thickness": 18, "material": "p", "grain": "x"},
    ]
    placements = [
        {"part_id": "a", "board_id": "b", "x": 0, "y": 0, "width": 40, "height": 20, "rotated": False},
        {"part_id": "b", "board_id": "b", "x": 41, "y": 0, "width": 21, "height": 40, "rotated": True},
    ]
    result = validate_plan([board], parts, placements, 3)
    assert result["valid"] is False
    assert result["checks"]["grain"] is False
    assert result["checks"]["dimensions"] is False
    assert result["checks"]["overlap_kerf"] is False or result["checks"]["bounds"] is False


def test_validator_catches_defect_and_bounds():
    board = {"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": [{"x": 0, "y": 0, "width": 20, "height": 100}]}
    part = {"id": "a", "width": 30, "height": 30, "thickness": 18, "material": "p", "grain": "x"}
    result = validate_plan([board], [part], [{"part_id": "a", "board_id": "b", "x": 15, "y": 80, "width": 30, "height": 30, "rotated": False}], 3)
    assert result["valid"] is False
    assert result["checks"]["defects"] is False
    assert result["checks"]["bounds"] is False


def test_no_fit_and_invalid_payloads():
    request = demo_request()
    request["boards"] = []
    request.pop("new_stock")
    result = solve(request)
    assert result["status"] == "no_fit"
    assert result["selected_design"] is None
    with pytest.raises(ValueError):
        solve({"design": {"width": True, "depth": 200, "height": 260, "thickness": 18}})
    with pytest.raises(ValueError):
        solve({"design": {"width": 600, "depth": 200, "height": 260, "thickness": 18}, "kerf": float("nan"), "boards": []})
    with pytest.raises(ValueError):
        solve({"design": {"width": 600, "depth": 200, "height": 260, "thickness": 18}, "boards": [{"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "x", "defects": [{}] * 9}]})


def test_repeatability_and_fingerprint():
    request = demo_request()
    first = solve(request)
    second = solve(copy.deepcopy(request))
    assert first == second
    json.dumps(first, sort_keys=True, allow_nan=False)
    assert len(first["input_fingerprint"]) == 64


def test_rotation_allowed_only_on_none_grain_board():
    board = {"id": "b", "width": 60, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": []}
    part = {"id": "a", "width": 100, "height": 60, "thickness": 18, "material": "p", "grain": "x"}
    placement = {"part_id": "a", "board_id": "b", "x": 0, "y": 0, "width": 60, "height": 100, "rotated": True}
    assert validate_plan([board], [part], [placement], 3)["valid"] is True


def test_validator_rejects_nonfinite_and_outside_defects_without_raising():
    board = {"id": "b", "width": float("nan"), "height": 100, "thickness": 18, "material": "p", "grain": "x", "defects": []}
    part = {"id": "a", "width": 30, "height": 30, "thickness": 18, "material": "p", "grain": "x"}
    result = validate_plan([board], [part], [], 3)
    assert result["valid"] is False
    assert result["checks"]["inputs"] is False

    board["width"] = 100
    board["defects"] = [{"x": 90, "y": 0, "width": 20, "height": 1}]
    result = validate_plan([board], [part], [], 3)
    assert result["valid"] is False
    assert any("invalid bounds" in error for error in result["errors"])


def test_validator_requires_kerf_gap_at_diagonal_corners():
    board = {"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": []}
    parts = [
        {"id": "a", "width": 40, "height": 40, "thickness": 18, "material": "p", "grain": "x"},
        {"id": "b", "width": 40, "height": 40, "thickness": 18, "material": "p", "grain": "x"},
    ]
    placements = [
        {"part_id": "a", "board_id": "b", "x": 0, "y": 0, "width": 40, "height": 40, "rotated": False},
        {"part_id": "b", "board_id": "b", "x": 41, "y": 41, "width": 40, "height": 40, "rotated": False},
    ]
    result = validate_plan([board], parts, placements, 3)
    assert result["valid"] is False
    assert result["checks"]["overlap_kerf"] is False


def test_validator_rejects_boolean_geometry():
    board = {"id": "b", "width": True, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": []}
    part = {"id": "a", "width": 30, "height": 30, "thickness": 18, "material": "p", "grain": "x"}
    result = validate_plan([board], [part], [], 3)
    assert result["valid"] is False
    assert result["checks"]["inputs"] is False


def test_zero_kerf_allows_exactly_adjacent_parts():
    board = {"id": "b", "width": 100, "height": 50, "thickness": 18, "material": "p", "grain": "x", "defects": []}
    parts = [
        {"id": "a", "width": 50, "height": 50, "thickness": 18, "material": "p", "grain": "x"},
        {"id": "b", "width": 50, "height": 50, "thickness": 18, "material": "p", "grain": "x"},
    ]
    placements = [
        {"part_id": "a", "board_id": "b", "x": 0, "y": 0, "width": 50, "height": 50, "rotated": False},
        {"part_id": "b", "board_id": "b", "x": 50, "y": 0, "width": 50, "height": 50, "rotated": False},
    ]
    assert validate_plan([board], parts, placements, 0)["valid"] is True


def test_rejects_width_without_two_positive_openings():
    request = demo_request()
    request["design"].update(width=150, min_width=100, thickness=60)
    with pytest.raises(ValueError):
        solve(request)


@pytest.mark.parametrize("field", ["width", "height", "thickness"])
def test_validator_rejects_nonfinite_board_and_part_fields(field):
    board = {"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": []}
    part = {"id": "a", "width": 20, "height": 20, "thickness": 18, "material": "p", "grain": "x"}
    board[field] = float("inf")
    part[field] = float("nan")
    result = validate_plan([board], [part], [], 3)
    assert result["valid"] is False
    assert result["checks"]["inputs"] is False


def test_validator_rejects_nonfinite_defect_fields():
    board = {"id": "b", "width": 100, "height": 100, "thickness": 18, "material": "p", "grain": "none", "defects": [{"x": float("inf"), "y": 0, "width": 1, "height": 1}]}
    part = {"id": "a", "width": 20, "height": 20, "thickness": 18, "material": "p", "grain": "x"}
    result = validate_plan([board], [part], [], 3)
    assert result["valid"] is False
    assert result["checks"]["inputs"] is False
