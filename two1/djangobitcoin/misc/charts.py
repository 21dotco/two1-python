import pygal
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
import sys

from two1.djangobitcoin.auth.djangobitcoin import PaymentRequiredAuthentication

"""
{
	"labels": ["South", "East", "North", "West"],
	"series": [{
		"Bitcoin": [200, 150, 300, 60]
	}, {
		"Litecoin": [20, 190, 40, 30]
	}],
	"title": "Cryptocurrencies"
}
"""


@api_view(['POST'])
@authentication_classes([PaymentRequiredAuthentication])
def chart(request):
    """
    Plots a bar chart as an SVG
    ---
    parameters:
        - name: chart_type
          description: Type of the chart
          required: true
          type: string
          paramType: query
          enum:
            - Line
            - StackedLine
            - Bar
            - StackedBar
            - HorizontalBar
            - Pie
            - Radar
            - Box
            - Dot
            - Funnel
            - Gauge
            - Treemap
        - name: data
          description: Data to be charted as a bar chart
          required: true
          type: string
          paramType: body
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query

    """
    chart_type = request.QUERY_PARAMS.get("chart_type", None)
    if not chart_type:
        return Response({"Error": "Must provide value for Chart Type parameter"})
    data = request.DATA
    if not data:
        return Response("Must provide value for Data parameter",status=400)

    chart = getattr(sys.modules[pygal.__name__], chart_type)()
    chart.title = data["title"]
    chart.x_labels = data["labels"]
    for series in data["series"]:
        label, data = series.popitem()
        chart.add(label, data)
    return chart.render_django_response()
