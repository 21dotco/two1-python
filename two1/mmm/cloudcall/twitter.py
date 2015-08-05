from rest_framework.decorators import api_view, authentication_classes
from lib.djangobitcoin import PaymentRequiredAuthentication
from rest_framework.response import Response
from birdy.twitter import UserClient


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def post_update(request):
    """
    Send an SMS
    ---
    type:
      result:
        type: string

    parameters:
        - name: update
          description: text of the twitter update to be published
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    update = request.data.get("update", None)
    if not update:
        return Response("Must provide value for Update parameter", 400)

    client = UserClient("awgIGlQRJOjuR2tL38f472tZi",
                        "VGycVOMNk6tSKep1Bp89cvwsBmzNjyRchoxtGvkVrxrmZU2wyy",
                        "3307300213-rtaEZv9cvjioUoq4nhvqTzUrfLX9qjZQI2IZa2h",
                        "nwKVaOyNgESeRG6ieKHiRFrQ1XdtrcdhVaiXug6VEBMUD")

    response = client.api.statuses.update.post(status=update)
    return Response(response.data)
