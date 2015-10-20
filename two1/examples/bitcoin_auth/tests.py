import json

from django.test import Client
from django.test import TestCase


class BitcoinAuthTestCase(TestCase):

    """Test bitcoin_auth library."""

    def test_402_status_code(self):
        """Ensure we're returned back a 402."""
        response = Client().get('/weather/current-temperature?place=94115')
        self.assertEqual(response.status_code, 402)

    def test_402_header(self):
        """Ensure that 402 header includes payment info."""
        response = Client().get('/weather/current-temperature?place=94115')
        self.assertIsNotNone(response._headers.get('bitcoin-address'))
        self.assertIsNotNone(response._headers.get('price'))
        self.assertIsNotNone(response._headers.get('username'))

    def test_bittransfer_handshake(self):
        """Test that we're returend a 402, followed by a 200 after payment."""
        response = Client().get('/weather/current-temperature?place=94115')
        self.assertEqual(response.status_code, 402)
        response = Client().get(
            '/weather/current-temperature?place=94103',
            HTTP_BITCOIN_CHEQUE=json.dumps({
                'payee_username': None,
                'description': '/weather/current-temperature?place=94115',
                'amount': 5000,
                'payee_address': '1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5',
                'payer': 'djangocto'
            }),
            HTTP_AUTHORIZATION="paidsig"
        )
        self.assertEqual(response.status_code, 200)

    def test_bad_bittransfer_handshake(self):
        """Test that we're not able to pass in a malformed bittransfer."""
        response = Client().get('/weather/current-temperature?place=94115')
        self.assertEqual(response.status_code, 402)
        response = Client().get(
            '/weather/current-temperature?place=94115',
            HTTP_BITCOIN_CHEQUE="banoodletransfer",
            HTTP_AUTHORIZATION="banoodlesig"
        )
        self.assertEqual(response.status_code, 402)
