import json
import requests

from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view


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
    headers = {
        'Origin': 'https://id.wsj.com',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macitosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'X-HTTP-Method-Override': 'POST',
    }
    payload = {
        "username": settings.WSJ_USERNAME,
        "password": settings.WSJ_PASSWORD,
        "url": request.data['url'],
        "template": "default",
        "realm": "default",
        "savelogin": "false"
    }
    response = requests.post(
        'https://id.wsj.com/auth/submitlogin.json',
        headers=headers,
        data=json.dumps(payload)
    )
    if response.ok:
        return Response({"paidurl": response.json()['url']})
    else:
        return Response({"error": response.json()})
