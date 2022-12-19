from helpers.holidays import get_bank_holidays


def test_get_bank_holidays():
    toto = get_bank_holidays()
    assert False