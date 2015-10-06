from rest_framework.decorators import api_view, authentication_classes
from bitcoin_auth.authentication import BasicPaymentRequiredAuthentication
from rest_framework.response import Response
from birdy.twitter import UserClient

CONSUMER_KEY = "CONSUMER_KEY"
CONSUMER_SECRET = "CONSUMER_SECRET"
ACCESS_TOKEN = "ACCESS_TOKEN"
ACCESS_TOKEN_SECRET = "ACCESS_TOKEN_SECRET"


@api_view(['POST'])
@authentication_classes([BasicPaymentRequiredAuthentication])
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

    client = UserClient(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    response = client.api.statuses.update.post(status=update)
    return Response(response.data)
