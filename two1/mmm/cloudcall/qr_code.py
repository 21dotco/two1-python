import qrcode
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes

from lib.djangobitcoin import PaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def generate(request):
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

    text = request.QUERY_PARAMS.get("text", None)
    if not text:
        return Response("Must provide value for Text parameter", code=400)
    response = HttpResponse(content_type="image/png")
    #    response["Cache-Control"] = "public, max-age=31536000"
    img = qrcode.make(text)
    img.save(response, "PNG")
    return response
