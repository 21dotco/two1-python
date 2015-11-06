import mock
from rest_framework.test import APITestCase, APIClient
from rest_framework import status


class MockRequest:

    """Class for mocking outgoing requests that any endpoint makes."""

    def __init__(self, text, ok):
        """Initialize the mock request."""
        self.text = text
        self.ok = ok


def fake_bing_search(*args, **kwargs):
    """Patch bing search so that it passes without an API key."""
    return MockRequest(['search result 1', 'search result 2'], True)


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
