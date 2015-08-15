import requests
from bs4 import BeautifulSoup
from lxml import etree
from lxml.cssselect import CSSSelector
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from auth.djangobitcoin import PaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def scrape_text(request):
    """
    Page text scraper
    ---
    type:
      result:
        type: string

    parameters:
        - name: url
          description: url of the web page to be scraped. Sample - https://medium.com/@21dotco/a-bitcoin-miner-in-every-device-and-in-every-hand-e315b40f2821
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
        return Response("Must provide value for Url parameter", 400)
    try:
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
        body = soup.getText()
        return Response(body)
    except Exception as e:
        pass
        return Response(e.args[0], 400)


@api_view(['GET'])
@authentication_classes([PaymentRequiredAuthentication])
def scrape_text_with_selector(request):
    """
    Page text scraper using XPath or CSS selector
    ---
    type:
      result:
        type: string

    parameters:
        - name: url
          description: url of the web page to be scraped. Sample - https://medium.com/@21dotco/a-bitcoin-miner-in-every-device-and-in-every-hand-e315b40f2821
          required: true
          type: string
          paramType: query
        - name: selector
          description: XPath selector or CSS selector to get text elements Sample //div[@class="section-inner layoutSingleColumn"]//text() (XPath) or .section-inner p (CSS)
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
        return Response("Must provide value for Url parameter", 400)
    selector = request.QUERY_PARAMS.get("selector", None)
    if not selector:
        return Response("Must provide value for Selector parameter", 400)
    try:
        tree = etree.fromstring(requests.get(url).text, etree.HTMLParser())
        if "/" in selector:  # assume XPath
            elements = tree.xpath(selector)
            body = ''.join(el for el in elements)
        else:
            elements = CSSSelector('.section-inner p,li')(tree)
            body = ''.join(el.text for el in elements if el.text)
        return Response(body)
    except Exception as e:
        pass
        return Response(e.args[0], 400)
