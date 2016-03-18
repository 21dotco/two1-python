from unittest.mock import MagicMock

from two1.wallet import fees


def test_get_fees():
    f = fees.get_fees()

    assert 'per_kb' in f
    assert 'per_input' in f
    assert 'per_output' in f

    assert f['per_kb'] >= 0 and f['per_kb'] <= 100000

    # Mock a response that doesn't have the correct data
    fees._fee_session.request = MagicMock(
        return_value=type('obj', (object,), {'status_code': 400,
                                             "json": lambda: "Not Json",
                                             'text': "Error"}))
    f = fees.get_fees()

    assert f['per_kb'] == fees.DEFAULT_FEE_PER_KB
