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
