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
