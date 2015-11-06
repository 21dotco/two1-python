from django.conf import settings
from two1.examples.bitcoin_auth.pricing import api_price
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from bing_search_api import BingSearchAPI


@api_price(800)
@api_view(["POST"])
def bing(request):
    """
    Search bing using a paid API.
    ---
    type:
      translated:
        type: string
    parameters:
        - name: query
          description: search query
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """
    if 'query' not in request.data:
        return Response({"error": "Must provide a 'query' parameter."},
                        status=status.HTTP_400_BAD_REQUEST)
    api = BingSearchAPI(settings.AZURE_MARKETPLACE_KEY)
    result = api.search_web(
        request.data['query'],
        payload={'$format': 'json'}
    )
    if result.ok:
        return Response({"results": result.text})
    else:
        return Response({"error": result.text},
                        status=status.HTTP_400_BAD_REQUEST)
