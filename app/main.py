import io
import time
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract
from .verification import evaluate

BASE = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
app = FastAPI(title='LabelLens | Human-in-the-loop TTB prototype', version='1.0.0')
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')

@app.get('/')
def index():
    return FileResponse(BASE / 'static' / 'index.html')

@app.get('/health')
def health():
    return {'ok': True}

@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...), brand: str = Form(''), abv: str = Form(''), volume: str = Form('')):
    if file.content_type not in {'image/jpeg', 'image/png', 'image/webp', 'image/tiff'}:
        raise HTTPException(400, 'Please upload a JPEG, PNG, WebP, or TIFF image.')
    blob = await file.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise HTTPException(413, 'Image must be 8 MB or smaller.')
    start = time.perf_counter()
    try:
        with Image.open(io.BytesIO(blob)) as src:
            if src.width * src.height > 20_000_000:
                raise HTTPException(413, 'Image dimensions too large (20 megapixel limit).')
            image = ImageOps.exif_transpose(src).convert('RGB')
            gray = ImageOps.autocontrast(ImageOps.grayscale(image))
            text = pytesseract.image_to_string(gray, config='--psm 11', timeout=12)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, 'Could not read this image; upload a clearer file.')
    except RuntimeError:
        raise HTTPException(504, 'OCR exceeded the processing time limit; try a smaller/clearer image.')
    result = evaluate(text, {'brand': brand, 'abv': abv, 'volume': volume})
    result.update({'filename': file.filename, 'duration_ms': round((time.perf_counter() - start) * 1000)})
    return result
