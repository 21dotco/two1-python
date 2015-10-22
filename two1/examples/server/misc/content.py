import json
import requests

from django.conf import settings
from two1.examples.bitcoin_auth.pricing import api_price
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_price(4000)
@api_view(["POST"])
def wsj(request):
    """
    Get a wsj article behind paywall
    ---
    type:
      translated:
        type: string
    parameters:
        - name: url
          description: URL of the WSJ article
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """
    article_url = request.data['url']
    # use our 3rd party paid WSJ scraper -> s3 uploader
    png_request = requests.post(
        settings.WSJ_PAID_SERVER_URL,
        data=json.dumps({
            "url": article_url,
            "auth_url": article_url
        }),
        headers={"Content-Type": "application/json"}
    )
    if png_request.ok:
        return Response({
            "article": png_request.json()["url"]
        })
    else:
        return Response({"error": png_request.text})
