from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes
from textblob import TextBlob

from two1.examples.auth.djangobitcoin import PaymentRequiredAuthentication


def get_text_to_be_processed(request):
    return request.data.get("text", None)


class LanguageProcessingPaymentRequired(PaymentRequiredAuthentication):
    def getQuoteFor(self, request):
        text = get_text_to_be_processed(request)
        if not text:
            return 0
        return len(text)  # I think satoshi per character is reasonable


@api_view(['POST'])
@authentication_classes([LanguageProcessingPaymentRequired])
def translate(request):
    """
    Translates provided text from English to Spanish
    ---
    type:
      translated:
        type: string
    parameters:
        - name: text
          description: Text to translate to other language
          required: false
          type: string
          paramType: form
        - name: from_language
          description: Source language
          required: false
          type: string
          paramType: form
        - name: to_language
          description: Target language
          required: false
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    blob = get_text_to_be_processed(request)
    if not blob:
        return Response("Must provide value for Text parameter", status=400)
    from_lang = request.data.get("from_language", None)
    to_lang = request.data.get("to_language", "en")
    blob = TextBlob(str(blob))
    return Response({"translated": str(blob.translate(from_lang=from_lang, to=to_lang))})


@api_view(['POST'])
@authentication_classes([LanguageProcessingPaymentRequired])
def sentiment_analysis(request):
    """
    Translates provided text from English to Spanish
    ---
    type:
      translated:
        type: string
    parameters:
        - name: text
          description: Text to perform sentiment analysis on
          required: true
          type: string
          paramType: form
        - name: tx
          description: Transaction Id  (proof of payment)
          type: string
          paramType: query
    """

    blob = get_text_to_be_processed(request)
    if not blob:
        return Response("Must provide value for Text parameter", status=400)
    blob = TextBlob(str(blob))
    (polarity, subjectivity) = blob.sentiment
    return Response({"polarity": polarity, "subjectivity": subjectivity})
