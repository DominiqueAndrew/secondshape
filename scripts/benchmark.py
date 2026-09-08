"""Deterministic synthetic scenario evidence, not a field impact study."""
import json
import time
from copy import deepcopy
from pathlib import Path

from secondshape.engine import demo_request, solve, validate_plan


def scenarios():
    base = demo_request()
    yield 'edge-damage-example', deepcopy(base)
    value = deepcopy(base)
    value['boards'][0]['width'] = 650
    value['boards'][0]['defects'] = []
    yield 'ideal-already-fits', value
    value = deepcopy(base)
    value['design']['min_width'] = 600
    value['design']['min_depth'] = 240
    yield 'no-dimension-concession', value
    value = deepcopy(base)
    value['boards'] = value['boards'][1:]
    yield 'missing-main-panel', value
    value = deepcopy(base)
    value['boards'][1]['thickness'] = 12
    yield 'incompatible-thickness', value
    value = deepcopy(base)
    value['kerf'] = 12
    yield 'wide-kerf', value
    value = deepcopy(base)
    value['boards'][0]['defects'] = [{'x':250,'y':50,'width':70,'height':150}]
    yield 'interior-damage', value
    value = deepcopy(base)
    value['boards'][1]['width'] = 260
    value['boards'][1]['height'] = 760
    value['boards'][1]['grain'] = 'none'
    yield 'rotation-needed', value


def main():
    output = Path(__file__).resolve().parents[1] / 'output' / 'benchmark'
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, request in scenarios():
        start = time.perf_counter()
        try:
            result = solve(request)
        except ValueError as error:
            assert name == 'incompatible-thickness', (name,str(error))
            results.append({'scenario':name,'status':'input_rejected','reason':str(error),'elapsed_seconds':round(time.perf_counter()-start,4)})
            continue
        seconds = time.perf_counter() - start
        verified = validate_plan(result['boards'], result['parts'], result['placements'], request['kerf'])
        assert verified['valid'] == (result['status'] == 'feasible'), name
        if name == 'no-dimension-concession':
            assert result['status'] == 'no_fit'
        if name == 'ideal-already-fits':
            assert result['selected_design']['width_mm'] == 600
        if result['status'] == 'feasible':
            corrupt = deepcopy(result['placements'])
            corrupt[0]['x'] = -1
            assert not validate_plan(result['boards'], result['parts'], corrupt, request['kerf'])['valid']
        (output / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        results.append({'scenario':name,'status':result['status'],'selected_design':result['selected_design'],'baseline_new_panels':result['baseline']['new_boards'],'certificate_valid':verified['valid'],'elapsed_seconds':round(seconds,4),'input_fingerprint':result['input_fingerprint']})
    report = {'evidence_type':'synthetic_fixture_measurement','field_validated':False,'scenarios':results}
    (output / 'report.json').write_text(json.dumps(report,indent=2) + '\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
