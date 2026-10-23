from app.verification import evaluate, _parse_volume, _parse_abv

def test_matching_fields_still_require_human_review():
    sample = 'OLD TOM DISTILLERY\nKentucky Straight Bourbon Whiskey\n45% Alc./Vol. (90 Proof)\n750 mL\n'
    out = evaluate(sample, {'brand': 'Old Tom Distillery', 'abv': '45%', 'volume': '750 mL'})
    assert out['checks']['brand']['status'] == 'pass'
    assert out['checks']['abv']['status'] == 'pass'
    assert out['checks']['volume']['status'] == 'pass'
    assert out['overall'] == 'mismatch'
    assert out['human_review_required'] is True

def test_mismatched_abv():
    out = evaluate('WHISKEY\n40% Alc./Vol.\n750 mL', {'abv': '45%', 'volume': '750mL'})
    assert out['checks']['abv']['status'] == 'mismatch'

def test_units():
    assert _parse_volume('75 cl') == 750
    assert _parse_volume('0.75 L') == 750
    assert _parse_abv('45% Alc./Vol.') == 45

def test_unknown_does_not_pass():
    out = evaluate('', {'brand': 'Bourbon', 'abv': '45%', 'volume': '750 mL'})
    assert out['checks']['abv']['status'] == 'review'
    assert out['checks']['volume']['status'] == 'review'
    assert out['checks']['brand']['status'] == 'mismatch'

def test_low_confidence_warning_requires_review():
    out = evaluate('OLD TOM DISTILLERY 45% 750 mt GOVERNMENT WARNlNG illegible',
                   {'brand': 'OLD TOM DISTILLERY', 'abv': '45%', 'volume': '750 mL'}, ocr_confidence=28)
    assert out['checks']['warning']['status'] == 'review'
    assert out['checks']['volume']['status'] == 'review'

def test_warning_wrong_case_flagged():
    from app.verification import WARNING
    out = evaluate(WARNING.replace('GOVERNMENT WARNING:', 'Government Warning:'), {}, ocr_confidence=96)
    assert out['checks']['warning']['status'] == 'mismatch'

def test_complete_warning_still_needs_human_review():
    from app.verification import WARNING
    out = evaluate(WARNING, {}, ocr_confidence=96)
    assert out['checks']['warning']['status'] == 'review'
    assert out['human_review_required']

def test_incomplete_warning_flagged_when_readable():
    out = evaluate('Brand 45% 750 mL GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects.', {}, ocr_confidence=95)
    assert out['checks']['warning']['status'] == 'mismatch'


def test_warning_hyphenation_and_ocr_zero_are_uncertain_not_violation():
    from app.verification import WARNING
    noisy = WARNING.replace('According', 'ACCORD- ING').replace('to drive', 't0 drive')
    out = evaluate(noisy, {}, ocr_confidence=85)
    assert out['checks']['warning']['status'] == 'review'


def test_warning_missing_second_section_still_mismatch():
    from app.verification import WARNING
    only_first = WARNING.split('(2)')[0]
    out = evaluate(only_first, {}, ocr_confidence=90)
    assert out['checks']['warning']['status'] == 'mismatch'


def test_low_quality_brand_missing_is_uncertain():
    out = evaluate('KEY COOKER S KENTUCKY WHS', {'brand': "BOOKER'S"}, ocr_confidence=25)
    assert out['checks']['brand']['status'] == 'review'


def test_optional_fields_match_when_supplied():
    text = 'OLD TOM DISTILLERY Kentucky Straight Bourbon Whiskey Produced by Example Distillery USA'
    result = evaluate(text, {'class_type': 'kentucky straight bourbon whiskey', 'producer': 'Example Distillery', 'origin': 'USA'})
    assert result['checks']['class_type']['status'] == 'pass'
    assert result['checks']['producer']['status'] == 'pass'
    assert result['checks']['origin']['status'] == 'pass'


def test_unreadable_optional_fields_trigger_review_not_rejection():
    result = evaluate('Old Tom 45% 750 mL', {'class_type': 'Whiskey', 'producer': 'Unknown Bottler', 'origin': 'Scotland'})
    assert all(result['checks'][key]['status'] == 'review' for key in ('class_type', 'producer', 'origin'))


def test_legacy_response_does_not_require_new_fields():
    result = evaluate('OLD TOM DISTILLERY 45% 750 mL', {'brand': 'OLD TOM DISTILLERY', 'abv': '45%', 'volume': '750 mL'})
    assert all(key not in result['checks'] for key in ('class_type','producer','origin'))
