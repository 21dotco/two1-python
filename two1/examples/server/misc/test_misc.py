import mock
from rest_framework import status
from rest_framework.test import APITestCase, APIClient


class MockRequest:

    """Class for mocking outgoing requests that any endpoint makes."""

    def __init__(self, **kwargs):
        """Initialize the mock request."""
        for key, val in kwargs.items():
            setattr(self, key, val)


def fake_bing_search(*args, **kwargs):
    """Patch bing search so that it passes without an API key."""
    return MockRequest(text=['search result 1', 'search result 2'], ok=True)


def fake_twilio_sms(*args, **kwargs):
    """Patch creating an SMS message so that it passes without an API key."""
    return MockRequest(status='good', body=kwargs['body'],
                       to=kwargs['to'], from_='+14155551234')

###############################################################################


class EndpointTests(APITestCase):

    """Test example server endpoints."""

    def setUp(self):
        """Set up a mock REST client for each test."""
        self.client = APIClient()

    @mock.patch('bing_search_api.BingSearchAPI.search_web', fake_bing_search)
    def test_search_bing(self):
        """Test bing search endpoint."""
        # Test initial response of 402
        bing_route = '/search/bing'
        unpaid = self.client.post(bing_route)
        self.assertEqual(unpaid.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        # Test paid response of 400 if bad parameters are provided
        search = self.client.post(bing_route, HTTP_BITCOIN_TRANSACTION='paid')
        self.assertEqual(search.status_code, status.HTTP_400_BAD_REQUEST)

        # Test paid response of 200 if good paramters are provided
        search = self.client.post(bing_route, {'query': 'test search'},
                                  HTTP_BITCOIN_TRANSACTION='paid')
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertIn('results', search.data)

    @mock.patch('twilio.rest.resources.Messages.create', fake_twilio_sms)
    def test_send_sms(self):
        """Test send SMS endpoint."""
        # Test initial response of 402
        sms_route = '/phone/send-sms'
        unpaid = self.client.post(sms_route)
        self.assertEqual(unpaid.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        # Test paid response of 400 if bad parameters are provided
        search = self.client.post(sms_route, HTTP_BITCOIN_TRANSACTION='paid')
        self.assertEqual(search.status_code, status.HTTP_400_BAD_REQUEST)

        # Test paid response of 200 if bad parameters are provided
        data = {'phone': '+12341231234', 'text': 'test message'}
        search = self.client.post(sms_route, data, HTTP_BITCOIN_TRANSACTION='paid')
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertEqual(search.data['to'], '+12341231234')
        self.assertEqual(search.data['body'], 'test message')
