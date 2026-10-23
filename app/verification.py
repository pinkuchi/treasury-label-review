"""Explainable, conservative comparisons for a human-in-the-loop label-review prototype."""
import re
from difflib import SequenceMatcher

WARNING = ("GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. "
           "(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.")

def normalized(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").casefold())

def verdict(status, expected=None, found=None, note=""):
    return {"status": status, "expected": expected, "found": found, "note": note}

def _candidate(lines, key):
    patterns = {
        'abv': r'\b(\d{1,2}(?:\.\d+)?)\s*%\s*(?:alc(?:ohol)?\.?\s*(?:/|per)?\s*vol(?:ume)?\.?)?',
        'volume': r'\b(\d+(?:\.\d+)?)\s*(mL|cl|L|fl\.?\s*oz)\b',
    }
    match = re.search(patterns[key], ' '.join(lines), re.I)
    return match.group(0).strip() if match else None

def _parse_abv(s):
    if not s: return None
    match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', s)
    return float(match.group(1)) if match else None

def _parse_volume(s):
    if not s: return None
    match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|cl|l|fl\.?\s*oz)\b', s, re.I)
    if not match: return None
    n, unit = float(match.group(1)), match.group(2).lower().replace('.', '').replace(' ', '')
    return round(n * {'ml': 1, 'cl': 10, 'l': 1000, 'floz': 29.5735295625}[unit], 2)

def evaluate(ocr_text: str, form: dict, ocr_confidence: float | None = None):
    lines = [re.sub(r'\s+', ' ', ln.strip()) for ln in ocr_text.splitlines() if ln.strip()]
    joined = ' '.join(lines)
    checks = {}
    brand = (form.get('brand') or '').strip()
    if brand:
        matching = max((SequenceMatcher(None, normalized(brand), normalized(line)).ratio() for line in lines), default=0)
        present = normalized(brand) in normalized(joined)
        checks['brand'] = verdict('pass' if present else 'review' if matching >= .78 or (ocr_confidence is not None and ocr_confidence < 60) else 'mismatch', brand,
                                  next((line for line in lines if normalized(brand) in normalized(line)), None),
                                  'Case, spacing and punctuation ignored; confirm visually.' if present else 'Brand not confidently identified; check label manually.')
    abv_expected = _parse_abv(form.get('abv', ''))
    abv_found_text = _candidate(lines, 'abv')
    abv_found = _parse_abv(abv_found_text)
    checks['abv'] = verdict('review' if abv_expected is None or abv_found is None else 'pass' if abs(abv_expected - abv_found) < .01 else 'mismatch',
                            form.get('abv') or None, abv_found_text, 'Numerical ABV check; OCR may confuse small print. Check proof and context manually.')
    volume_expected = _parse_volume(form.get('volume', ''))
    volume_found_text = _candidate(lines, 'volume')
    volume_found = _parse_volume(volume_found_text)
    checks['volume'] = verdict('review' if volume_expected is None or volume_found is None else 'pass' if abs(volume_expected - volume_found) < .5 else 'mismatch',
                               form.get('volume') or None, volume_found_text, 'Converted to milliliters for comparison.')
    # OCR inserts hyphenated line breaks and character substitutions on bottles.
    # Approximate comparison only prevents false mismatch; it never proves compliance.
    compact = re.sub(r'\s+', ' ', joined).strip()
    canonical = re.sub(r'(?<=\w)-\s+(?=\w)', '', compact)
    evidence = normalized(canonical)
    low_quality = ocr_confidence is not None and ocr_confidence < 60
    warning_fragments = any(term in evidence for term in
        ('governmentwarning', 'surgeongeneral', 'birthdefects', 'healthproblems'))
    has_header = 'GOVERNMENT WARNING:' in joined
    has_wrong_case_header = bool(re.search(r'government\s+warning\s*:', joined, re.I)) and not has_header
    full_text = normalized(WARNING) in evidence
    near_start = any(t in evidence for t in ('surgeongeneral', 'pregnancy', 'birthdefects'))
    near_end = any(t in evidence for t in ('healthproblems', 'operatemachinery', 'abilitytodrive'))
    header = re.search(r'government\s*warning\s*:', canonical, re.I)
    candidate = canonical[header.start():] if header else canonical
    target = normalized(WARNING)
    candidate = normalized(candidate)[:len(target) + 60]
    similarity = SequenceMatcher(None, target, candidate, autojunk=False).ratio()
    fuzzy_complete = near_start and near_end and similarity >= 0.68
    if low_quality:
        warning_status = 'review'
        warning_note = 'Low OCR confidence: warning cannot be reliably evaluated. Request clearer artwork.'
    elif has_wrong_case_header:
        warning_status = 'mismatch'
        warning_note = 'Warning heading may not be uppercase; inspect original artwork.'
    elif has_header and full_text:
        warning_status = 'review'
        warning_note = 'OCR text resembles the full reference statement; verify exact wording, bold heading and placement visually.'
    elif fuzzy_complete:
        warning_status = 'review'
        warning_note = 'Both warning sections appear present, but OCR has differences; visually verify every word, heading and formatting.'
    elif warning_fragments:
        warning_status = 'mismatch'
        warning_note = 'Only part of the warning was recognized; inspect original label for missing text or OCR errors.'
    else:
        warning_status = 'mismatch' if compact and len(compact) > 35 else 'review'
        warning_note = ('No health warning recognized in readable text; check that the image includes the correct panel.'
                        if warning_status == 'mismatch' else 'Warning could not be read; request clearer artwork or another panel.')
    checks['warning'] = verdict(warning_status, 'Statutory Government Health Warning',
                                'Full text detected' if has_header and full_text else 'Detected fragments / uncertain',
                                warning_note)
    statuses = [v['status'] for v in checks.values()]
    overall = 'mismatch' if 'mismatch' in statuses else 'review' if 'review' in statuses else 'pass'
    if overall == 'pass': overall = 'review'
    return {'overall': overall, 'checks': checks, 'ocr_text': ocr_text, 'human_review_required': True,
            'notice': 'Screening assistance only; this tool does not approve or reject labels or replace a TTB compliance officer.'}
