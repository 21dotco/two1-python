import json
from django.http import HttpResponse
import requests
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from auth.djangobitcoin import PaymentRequiredAuthentication


def wunderground_request(query, place):
    return json.loads(
        requests.get("http://api.wunderground.com/api/f1deaf62cc9bfcf0/{0}/q/{1}.json".format(query, place)).text)


def wunderground_radar_request(query, place):
    return requests.get(
        "http://api.wunderground.com/api/f1deaf62cc9bfcf0/{0}/q/{1}.gif?newmaps=1&timelabel=1&timelabel.y=10&num=5&delay=50".format(
            query, place))


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def current_temperature(request):
    """
    Current temperature for location
    ---
    type:
      result:
        type: string

    parameters:
        - name: place
          description: one of the following - State/City, Zip code, Latitude,Longitude
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    place = request.QUERY_PARAMS.get("place", None)
    if not place:
        return Response("Must provide value for Place parameter", code=400)
    return Response(wunderground_request("conditions", place)["current_observation"]["temp_f"])


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def forecast(request):
    """
    Weather forecast by location
    ---
    type:
      result:
        type: string

    parameters:
        - name: place
          description: one of the following - State/City, Zip code, Latitude,Longitude
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    place = request.QUERY_PARAMS.get("place", None)
    if not place:
        return Response("Must provide value for Place parameter", code=400)
    return Response(wunderground_request("forecast", place))


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def radar(request):
    """
    Radar image by location
    ---
    type:
      result:
        type: string

    parameters:
        - name: place
          description: one of the following - State/City, Zip code, Latitude,Longitude
          required: true
          type: string
          paramType: query
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    place = request.QUERY_PARAMS.get("place", None)
    if not place:
        return Response("Must provide value for Place parameter", code=400)
    radar_response = wunderground_radar_request("animatedradar", place)
    return HttpResponse(radar_response.content, content_type=radar_response.headers["content-type"])
