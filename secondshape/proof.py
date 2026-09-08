"""Bind an exported geometry certificate back to its five-panel design brief.

This checks the submitted result without running the packing search again.
Fingerprints are reproducibility identifiers, not signatures or evidence that
the physical material was measured correctly.
"""
import hashlib
import json
import math

from .engine import validate_plan


def verify_export(payload):
    errors = []
    checks = {'brief': True, 'inventory': True, 'fingerprint': True}
    try:
        if not isinstance(payload, dict):
            raise ValueError('The proof must be an object.')
        request = payload['request']
        if not isinstance(request, dict):
            raise ValueError('The request must be an object.')
        design = request['design']
        if not isinstance(design, dict):
            raise ValueError('The design must be an object.')
        placements = payload.get('placements')
        if not isinstance(placements, list) or len(placements) != 5:
            raise ValueError('The organizer requires exactly five placements.')
        selected = payload['selected_design']
        if not isinstance(selected, dict):
            raise ValueError('There is no selected salvage design to verify.')

        def finite(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

        for key in ['width', 'depth', 'height', 'thickness', 'min_width', 'min_depth']:
            if not finite(design.get(key)):
                raise ValueError(f'Invalid brief dimension: {key}')
        for key in ['width_mm', 'depth_mm', 'height_mm', 'thickness_mm']:
            if not finite(selected.get(key)):
                raise ValueError(f'Invalid selected dimension: {key}')
        width, depth = selected['width_mm'], selected['depth_mm']
        height, thickness = design['height'], design['thickness']
        if not design['min_width'] <= width <= design['width'] or not design['min_depth'] <= depth <= design['depth']:
            raise ValueError('Selected dimensions fall outside the brief.')
        if selected['height_mm'] != height or selected['thickness_mm'] != thickness or height <= 2*thickness or width <= 3*thickness:
            raise ValueError('Selected height or thickness does not match the brief.')
        inventory = request['boards']
        if not isinstance(inventory, list) or len(inventory) > 6 or not all(isinstance(b,dict) for b in inventory):
            raise ValueError('The inventory must contain at most six boards.')
        material = inventory[0]['material'] if inventory else 'salvaged-material'
        inner = height-2*thickness
        expected = [
            {'id': name, 'width_mm': width if name in ('top','base') else inner,
             'height_mm': depth, 'thickness_mm': thickness, 'material': material, 'grain':'x'}
            for name in ['top','base','side-1','side-2','divider']
        ]
        actual = payload['parts']
        if not isinstance(actual,list) or len(actual) != 5 or not all(isinstance(p,dict) for p in actual):
            raise ValueError('The organizer requires exactly five parts.')
        actual_by_id = {p.get('id'):p for p in actual}
        if set(actual_by_id) != {p['id'] for p in expected}:
            raise ValueError('A mandatory organizer part is missing or duplicated.')
        for part in expected:
            if any(actual_by_id[part['id']].get(k) != v for k,v in part.items()):
                raise ValueError(f"Part {part['id']} does not match the selected design.")
        exported_boards = payload['boards']
        if not isinstance(exported_boards,list) or len(exported_boards) > 6:
            raise ValueError('The exported board list is invalid.')
        inventory_by_id = {b['id']:b for b in inventory}
        if len(inventory_by_id) != len(inventory):
            raise ValueError('Inventory board IDs must be unique.')
        for board in exported_boards:
            if not isinstance(board,dict) or board.get('id') not in inventory_by_id or board != inventory_by_id[board['id']]:
                checks['inventory'] = False
                errors.append('An exported board does not match the input inventory.')
        canonical = json.dumps(request, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        if hashlib.sha256(canonical.encode()).hexdigest() != payload.get('input_fingerprint'):
            checks['fingerprint'] = False
            errors.append('The input fingerprint does not match the exported request.')
        geometry = validate_plan(exported_boards, expected, payload['placements'], request['kerf'])
        return {'valid': geometry['valid'] and not errors, 'checks': {**geometry['checks'], **checks}, 'errors': geometry['errors']+errors}
    except (KeyError, TypeError, ValueError) as error:
        checks['brief'] = False
        return {'valid': False, 'checks':checks, 'errors': [str(error)]}
