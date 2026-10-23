import io
import os
import time
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract
from pytesseract import Output
from .verification import evaluate

os.environ.setdefault('OMP_THREAD_LIMIT', '1')  # Avoid oversubscribing tiny Render Free CPUs.
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
            # Keep the image small: Tesseract on the Render free CPU is slow
            # even when a phone photo is well below the upload-size limit.
            image = ImageOps.exif_transpose(src).convert('RGB')
            image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
            gray = ImageOps.autocontrast(ImageOps.grayscale(image))
            # Single-threaded Tesseract avoids CPU contention on small instances.
            # One attempt with a short fixed deadline; do not double the wait on failure.
            data = pytesseract.image_to_data(
                gray, config='--psm 11', output_type=Output.DICT, timeout=9)
            words = [t for t in data['text'] if t and t.strip()]
            text = ' '.join(words)
            confidences = [float(c) for c, t in zip(data['conf'], data['text']) if t and t.strip() and float(c) >= 0]
            ocr_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, 'Could not read this image; upload a clearer file.')
    except RuntimeError:
        raise HTTPException(503, 'OCR worker is overloaded; please retry or upload a cropped label image.')
    result = evaluate(text, {'brand': brand, 'abv': abv, 'volume': volume}, ocr_confidence=ocr_confidence)
    result.update({'filename': file.filename, 'duration_ms': round((time.perf_counter() - start) * 1000)})
    return result
