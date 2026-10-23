"""HTTP endpoint regression tests. Run: python -m pytest -q."""
from io import BytesIO
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_label(text='OLD TOM DISTILLERY 45% 750 mL'):
    image = Image.new('RGB', (900, 240), 'white')
    ImageDraw.Draw(image).text((20, 40), text, fill='black')
    out = BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['ok'] is True


def test_analyze_png_response_contract():
    response = client.post('/api/analyze',
        files={'file': ('label.png', make_label(), 'image/png')},
        data={'brand': 'OLD TOM DISTILLERY', 'abv': '45%', 'volume': '750 mL'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['filename'] == 'label.png'
    assert result['human_review_required']
    assert result['overall'] in ('review', 'mismatch')
    assert {'brand', 'abv', 'volume', 'warning'} <= set(result['checks'])
    assert isinstance(result['ocr_text'], str)
    assert result['duration_ms'] >= 0


def test_optional_fields_backwards_compatible():
    response = client.post('/api/analyze',
        files={'file': ('label.png', make_label(), 'image/png')},
        data={'brand': 'OLD TOM DISTILLERY', 'class_type': 'Bourbon', 'producer': 'EXAMPLE', 'origin': 'USA'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert {'class_type', 'producer', 'origin'} <= set(result['checks'])
    assert all(result['checks'][key]['status'] in ('pass', 'review') for key in ('class_type', 'producer', 'origin'))


def test_bad_mime_rejected():
    response = client.post('/api/analyze',
        files={'file': ('bad.txt', b'hello', 'text/plain')})
    assert response.status_code == 400


def test_corrupt_image_rejected():
    response = client.post('/api/analyze',
        files={'file': ('bad.png', b'not a PNG', 'image/png')})
    assert response.status_code == 400


def test_oversize_upload_rejected():
    response = client.post('/api/analyze',
        files={'file': ('large.png', b'0' * (8 * 1024 * 1024 + 1), 'image/png')})
    assert response.status_code == 413
