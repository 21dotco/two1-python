from unittest import mock

from two1.wallet import fees


def test_get_fees():
    # Mock a response that doesn't have the correct data
    with mock.patch('two1.wallet.fees.requests.get') as mock_request:
        mock_request.return_value.status_code = 400
        f = fees.get_fees()

    assert f['per_kb'] == fees.DEFAULT_FEE_PER_KB
