import json

import qrcode
import requests
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes
from bitcoin_auth.authentication import BasicPaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([BasicPaymentRequiredAuthentication])
def generate_qr(request):
    """
    Serves a qr code
    ---
    parameters:
        - name: text
          description: Text to transform to barcode
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
    response = HttpResponse(content_type="image/png")
    img = qrcode.make(text)
    img.save(response, "PNG")
    return response


@api_view(['GET'])
@authentication_classes([BasicPaymentRequiredAuthentication])
def upc_lookup(request):
    """
    Searches UPC database
    ---
    type:
      result:
        type: string

    parameters:
        - name: upc
          description: Barcode to be found
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    upc = request.query_params.get("upc", None)
    if not upc:
        return Response("Must provide value for Url parameter", 400)
    response = requests.get("http://api.upcdatabase.org/json/84018dcccb9479a88c2de6cc3367a9c5/0071142000500")
    return Response(json.loads(response.text))
