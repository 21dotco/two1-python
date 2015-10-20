import requests
from requests_oauthlib import OAuth1

from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(["POST"])
def twitter(request):
    """
    Send myself a twitter DM as myself.
    ---
    type:
      translated:
        type: string
    parameters:
        - name: text
          description: message to send, include your @handle
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """
    oauth = OAuth1(
        settings.TWITTER_CONSUMER_KEY,
        client_secret=settings.TWITTER_CONSUMER_SECRET,
        resource_owner_key=settings.TWITTER_OAUTH_TOKEN,
        resource_owner_secret=settings.TWITTER_OAUTH_TOKEN_SECRET,
    )
    twitter_response = requests.post(
        'https://api.twitter.com/1.1/direct_messages/new.json',
        data={
            "screen_name": settings.TWITTER_HANDLE,
            "text": request.data["text"]
        },
        auth=oauth
    )
    if twitter_response.ok:
        return Response({
                "success": twitter_response.json()["text"]
            })
    else:
        return Response({
                "error": twitter_response.text
            })
