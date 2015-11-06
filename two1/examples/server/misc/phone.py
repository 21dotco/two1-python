import json
import requests

from django.conf import settings
from twilio.rest import TwilioRestClient
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from two1.examples.bitcoin_auth.pricing import api_price


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
    """
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
    )
    phone_number = request.data.get("phone", None)
    if not phone_number:
        return Response({"error": "Must provide value for 'phone' parameter"},
                        status=status.HTTP_400_BAD_REQUEST)
    text = request.data.get("text", None)
    if not text:
        return Response({"error": "Must provide value for 'text' parameter"},
                        status=status.HTTP_400_BAD_REQUEST)
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
