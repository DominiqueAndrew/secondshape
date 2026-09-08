"""HTTP boundary checks, separate from geometry unit tests."""
from app import app


def test_health_and_static():
    with app.test_client() as client:
        assert client.get('/api/health').json['engine'] == 'python'
        page = client.get('/')
        assert page.status_code == 200
        assert b'Let the' in page.data
        assert 'frame-ancestors' in page.headers['Content-Security-Policy']
        assert client.get('/static/app.js').status_code == 200


def test_bad_requests():
    with app.test_client() as client:
        assert client.post('/api/solve', json=[]).status_code == 400
        assert client.post('/api/solve', json={}).status_code == 400
        assert client.post('/api/solve', data='{', content_type='application/json').status_code == 400
        assert client.post('/api/solve', data='x' * 100_001, content_type='application/json').status_code == 413


def test_example_solve_and_independent_recheck():
    with app.test_client() as client:
        data = client.get('/api/example').json
        response = client.post('/api/solve', json=data)
        assert response.status_code == 200, response.json
        result = response.json
        assert result['status'] == 'feasible'
        assert result['certificate']['valid']
        assert client.post('/api/verify', json=result).json['valid']
        result['placements'][0]['x'] = -5
        assert not client.post('/api/verify', json=result).json['valid']


def test_export_cannot_drop_required_parts_or_rewrite_inventory():
    import copy
    with app.test_client() as client:
        result = client.post('/api/solve',json=client.get('/api/example').json).json
        altered = copy.deepcopy(result)
        dropped = altered['placements'].pop()['part_id']
        altered['parts'] = [part for part in altered['parts'] if part['id'] != dropped]
        assert not client.post('/api/verify',json=altered).json['valid']


def test_malformed_nested_proof_and_duplicate_flood_fail_closed():
    import copy
    with app.test_client() as client:
        result = client.post('/api/solve',json=client.get('/api/example').json).json
        for bad in [[], None, 'invalid', True]:
            altered = copy.deepcopy(result)
            altered['request']['design'] = bad
            response = client.post('/api/verify',json=altered)
            assert response.status_code == 200
            assert not response.json['valid']
            assert len(response.json['errors']) == 1
        altered = copy.deepcopy(result)
        altered['placements'] = [altered['placements'][0]]*600
        response = client.post('/api/verify',json=altered)
        assert response.status_code == 200
        assert not response.json['valid']
        assert len(response.json['errors']) == 1
        altered = copy.deepcopy(result)
        altered['boards'][0]['defects'] = []
        assert not client.post('/api/verify',json=altered).json['valid']
        altered = copy.deepcopy(result)
        altered['input_fingerprint'] = '0'*64
        assert not client.post('/api/verify',json=altered).json['valid']
