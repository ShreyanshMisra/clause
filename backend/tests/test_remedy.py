from app.remedy import compute_damages, money


def test_treble_deposit_under_15b():
    d = compute_damages("186-15B", {"security_deposit": 1500.0, "monthly_rent": 2000.0})
    assert d.amount == 4500.0
    assert "treble" in d.basis.lower()


def test_quiet_enjoyment_three_months_rent_under_186_14():
    d = compute_damages("186-14", {"security_deposit": 1500.0, "monthly_rent": 2000.0})
    assert d.amount == 6000.0
    assert "quiet enjoyment" in d.basis.lower()


def test_reprisal_three_months_rent_under_186_18():
    d = compute_damages("186-18", {"monthly_rent": 2000.0})
    assert d.amount == 6000.0


def test_unknown_statute_returns_none():
    assert compute_damages("93A-9", {"monthly_rent": 2000.0}).amount is None
    assert compute_damages("999", {}).amount is None


def test_missing_input_returns_none():
    assert compute_damages("186-15B", {}).amount is None
    assert compute_damages("186-14", {"security_deposit": 1500.0}).amount is None


def test_money_parses_currency_strings():
    assert money("$1,500") == 1500.0
    assert money("2000.50") == 2000.50
    assert money("") is None
    assert money(None) is None
    assert money("no digits") is None
