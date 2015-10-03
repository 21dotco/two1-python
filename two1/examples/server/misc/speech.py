import urllib

import requests
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from two1.examples.auth.djangobitcoin import PaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def text_to_speech(request):
    """
    Converts text to mp3
    ---
    type:
      result:
        type: string

    parameters:
        - name: text
          description: Text to be converted to speech
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query

    """

    text = request.query_params.get("text", None)
    if not text:
        return Response("Must provide value for Text parameter", 400)
    response = requests.get("http://tts-api.com/tts.mp3?q=" + urllib.parse.quote_plus(text))
    return HttpResponse(response.content, content_type=response.headers["content-type"])
