from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view

from bing_search_api import BingSearchAPI


@api_view(["POST"])
def bing(request):
    """
    Search bing using a paid API.
    ---
    type:
      translated:
        type: string
    parameters:
        - name: terms
          description: search terms
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """
    api = BingSearchAPI(settings.AZURE_MARKETPLACE_KEY)
    result = api.search_web(
        request.data['terms'],
        payload={'$format': 'json'}
    )
    if result.ok:
        return Response({"results": result.text})
    else:
        return Response({"Error": result.text})
