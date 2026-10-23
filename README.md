# LabelLens — Treasury Take-Home Assessment

An explainable, human-in-the-loop alcohol label review prototype. Upload an image of an alcohol beverage label, enter the application’s expected brand, alcohol percentage and volume, and receive an OCR-assisted field comparison.

## Features
- Upload JPEG, PNG, WebP, or TIFF images up to 8MB.
- Extract printed text with Tesseract OCR.
- Compare brand, alcohol by volume, and net contents to expected application data.
- Screen for the government health warning and flag uncertainty for human review.
- Review multiple labels in the web interface.
- Display extracted text and per-field reasons for each decision.
- No external AI service or keys needed.

**Important:** This is a screening prototype, not a TTB approval system. OCR cannot establish warning typography, statutory accuracy, label placement, or compliance exceptions. Human review is always required.

## Local startup
Requires Python 3.11+ and Tesseract OCR installed.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://localhost:8000 . Health check: `/health`.

## Testing
```bash
python -m pytest -q
```

## Docker
```bash
docker build -t treasury-label-review .
docker run --rm -p 8000:8000 treasury-label-review
```

## Render
The `render.yaml` Blueprint config and `Dockerfile` are included. Deploy as a Docker Web Service (or create a Blueprint) from this repository. Validate a public URL manually before submitting.

## Technology
FastAPI handles image uploads and validation; Pillow normalizes images; pytesseract runs Tesseract OCR; a deterministic comparator produces auditable statuses. The lightweight browser UI does not require Node or a paid API.

## Limitations and future enhancements
- Text extraction quality depends on image resolution, curvature, lighting, and language.
- Regulatory checks are intentionally conservative; they are not legal determinations.
- Checks do not comprehensively cover all product-specific TTB label rules.
- Future work: bounding boxes, OCR confidence, proof/ABV cross-checks, better volume normalization, and audit history.

## Assessment
Read original instructions: https://github.com/treasurytakehome-rgb/instructions

Designed to prioritize a functional prototype, explainability, and a reproducible Docker deployment.


## Extended screening (optional)
The existing brand, ABV, volume and Government Health Warning checks are unchanged. You may also enter **class/type**, **producer/bottler**, and **country of origin** for imports. Optional field checks are literal normalized OCR text matches. If text cannot be confidently found, the result is **REVIEW**, not a regulatory rejection; photographic OCR cannot prove that a required field is truly missing.

## Batch import with distinct application data
The upload widget accepts up to 20 label images per run. For different products, attach an optional CSV with columns:

```csv
filename,brand,abv,volume,class_type,producer,origin
label-a.png,OLD TOM DISTILLERY,45%,750 mL,Kentucky Straight Bourbon Whiskey,,
label-b.jpg,STONE'S THROW,40%,750 mL,,,Scotland
```

Filenames must exactly match uploaded images, including extension and capitalization. When no CSV is provided, the same manually entered application fields are used for every image (original workflow). Processing is sequential to prevent resource saturation. After reviewing, click **Export results CSV** to download per-image outcomes, checks, response durations, and errors. CSV records are parsed in the browser, and uploaded images are processed in memory rather than being persisted by this prototype.

## Architecture and decisions
Browser (HTML/CSS/vanilla JS) → multipart FastAPI `POST /api/analyze` → Pillow orientation/grayscale/contrast/resize → local Tesseract OCR (`psm 11`, OpenMP one-thread, bounded deadline) → explainable, deterministic Python comparison → JSON verdict with original OCR evidence → agent review.

Tesseract avoids sending artwork to external third-party OCR APIs, recurring API costs, and reliance on outbound network calls, a stated infrastructure concern. Render Docker ensures its system dependency is included. The system deliberately never labels a product as officially approved. Cases with unreadable warning typography or uncertain supplemental fields require visual review. OCR cannot confirm boldness, full statutory compliance, or whether a missing text field exists elsewhere on a multipanel label. Performance depends on instance CPU and photograph quality; the approximately-five-second target must be measured on production, not asserted from local timings.

## Verification and acceptance
- `python -m pytest -q` exercises comparators and regression cases, including warning OCR noise.
- Test clean, mismatch, missing warning, low-quality, and real-photograph examples; record HTTP status, overall verdict, per-field checks, and latency.
- Verify that CSV filenames map to the correct applications; duplicate filenames or absent mappings fail explicitly.
- Validate deploy availability at `/health` and end-to-end `/api/analyze` before assessment submission.
- Security/operational trade-offs: public prototype endpoint has upload file-size and pixel-count caps but no authentication, rate limiting, or persistent audit trail; it must not be used for sensitive real applications or production regulatory decisions.
