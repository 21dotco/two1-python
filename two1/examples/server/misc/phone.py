import json
import requests

from django.conf import settings
from twilio.rest import TwilioRestClient
from rest_framework.response import Response
from rest_framework.decorators import api_view
from two1.examples.bitcoin_auth.pricing import api_price


@api_view(['GET'])
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

    phone_number = request.query_params.get("phone", None)
    if not phone_number:
        return Response("Must provide value for Phone parameter", code=400)
    response = requests.get(
        "https://api.opencnam.com/v2/phone/{0}?format=json".format(
            phone_number
        ))
    return Response(json.loads(response.text))


@api_price(1000)
@api_view(['POST'])
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
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
    )
    phone_number = request.data.get("phone", None)
    if not phone_number:
        return Response("Must provide value for Phone parameter", code=400)
    text = request.data.get("text", None)
    if not text:
        return Response("Must provide value for Text parameter", code=400)
    response = client.messages.create(
        to=phone_number,
        from_=settings.TWILIO_NUMBER,
        body=text
    )
    return Response({
        "status": response.status,
        "body": response.body,
        "to": response.to,
        "from": response.from_
    })
