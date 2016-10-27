from unittest import TestCase
from unittest import mock

from two1.wallet import exceptions
from two1.wallet import fees


def test_get_fees_cointape_server_down():
    # Mock a response that doesn't have the correct data
    with mock.patch('two1.wallet.fees.requests.get') as mock_request:
        mock_request.return_value.status_code = 400
        f = fees.get_fees()

    assert f['per_kb'] == fees.DEFAULT_FEE_PER_KB


def test_get_fees_unreasonable_fee():
    with mock.patch('two1.wallet.fees.requests.get') as mock_request:
        return_value = mock_request.return_value
        return_value.status_code = 200
        fee_per_byte = fees.DEFAULT_FEE_PER_KB / 1000
        return_value.json = lambda: {
            'halfHourFee': fee_per_byte * 10,
        }
        with TestCase().assertRaises(exceptions.UnreasonableFeeError):
            fees.get_fees()
