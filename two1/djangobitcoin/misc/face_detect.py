import json
from django.http import HttpResponse

import requests
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from two1.djangobitcoin.auth.djangobitcoin import PaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def detect_from_url(request):
    """
    Detects faces using an image uri
    ---
    type:
      result:
        type: string

    parameters:
        - name: url
          description: Url of the image to be analyzed
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    url = request.QUERY_PARAMS.get("url", None)
    if not url:
        return Response("Must provide value for Url parameter", status=400)
    response = requests.post("https://api.projectoxford.ai/face/v0/detections?analyzesAge=true&analyzesGender=true",
                             data=json.dumps({"url": url}),
                             headers={"Ocp-Apim-Subscription-Key": "95cd8371476640d9b21b7a65b8683cd7"}
                             )
    return Response(json.loads(response.text))


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def detect_from_file(request):
    """
    Detects faces using an image file
    ---
    type:
      result:
        type: string

    parameters:
        - name: image
          description: File of the image to be analyzed
          required: true
          type: file
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query

    """

    file = request.FILES.get("image", None)
    if not file:
        return Response("Must provide file for Image parameter", status=400)

    response = requests.post("https://api.projectoxford.ai/face/v0/detections?analyzesAge=true&analyzesGender=true",
                             data=file,
                             headers={"Ocp-Apim-Subscription-Key": "95cd8371476640d9b21b7a65b8683cd7",
                                      "content-type": "application/octet-stream"}
                             )

    return Response(json.loads(response.text))


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def detect2_from_file(request):
    """
    Detects faces using an image file
    ---
    type:
      result:
        type: string

    parameters:
        - name: image
          description: File of the image to be analyzed
          required: true
          type: file
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query

    """

    file = request.FILES.get("image", None)
    if not file:
        return Response("Must provide file for Image parameter", status=400)

    response = requests.put("http://schnaps.trouble307.com:8080/v0/faces/detect",
                            data=file,
                            headers={"content-type": "image/png"})
    return Response(json.loads(response.text))


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def extract_from_file(request):
    """
    Extracts faces from an image file
    ---
    type:
      result:
        type: string

    parameters:
        - name: image
          description: File of the image to be analyzed
          required: true
          type: file
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query

    """

    file = request.FILES.get("image", None)
    if not file:
        return Response("Must provide file for Image parameter", status=400)

    response = requests.put("http://schnaps.trouble307.com:8080/v0/faces/extract",
                            data=file,
                            headers={"content-type": "image/png"})
    response_json = json.loads(response.text)
    return HttpResponse("".join(
        '<img src="data:image/png;base64,{0}"></img>'.format(face["image"]) for face in response_json["faces"]))
