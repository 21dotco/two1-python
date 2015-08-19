import json

import requests
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from two1.djangobitcoin.auth.djangobitcoin import PaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def phone_lookup(request):
    """
    Reverse phone lookup
    ---
    type:
      result:
        type: string

    parameters:
        - name: phone
          description: phone number to look up
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    phone_number = request.QUERY_PARAMS.get("phone", None)
    if not phone_number:
        return Response("Must provide value for Phone parameter", code=400)
    response = requests.get("https://api.opencnam.com/v2/phone/{0}?format=json".format(phone_number))
    return Response(json.loads(response.text))


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def send_sms(request):
    """
    Send an SMS
    ---
    type:
      result:
        type: string

    parameters:
        - name: phone
          description: phone number to send SMS to
          required: true
          type: string
          paramType: form
        - name: text
          description: SMS content
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    phone_number = request.data.get("phone", None)
    if not phone_number:
        return Response("Must provide value for Phone parameter", code=400)
    text = request.data.get("text", None)
    if not text:
        return Response("Must provide value for Text parameter", code=400)
    response = requests.post("http://textbelt.com/text", data={"number": phone_number, "message": text})
    return Response(json.loads(response.text))
