from django.conf.urls import url
from misc import barcode, charts, language, speech, face_detect, phone, charts, weather, image_processing, \
    scraper, blackjack, twitter

urlpatterns = [
    url(r'^barcode/generate-qr', barcode.generate_qr),
    url(r'^barcode/upc-lookup', barcode.upc_lookup),
    url(r'^charts/chart', charts.chart),
    url(r'^facedetect/detect-from-url', face_detect.detect_from_url),
    url(r'^facedetect/detect-from-file', face_detect.detect_from_file),
    url(r'^facedetect/detect2-from-file', face_detect.detect2_from_file),
    url(r'^facedetect/extract-from-file', face_detect.extract_from_file),
    url(r'^language/translate', language.translate),
    url(r'^language/sentiment-analysis', language.sentiment_analysis),
    url(r'^phone/phone-lookup', phone.phone_lookup),
    url(r'^phone/send-sms', phone.send_sms),
    url(r'^speech/text-to-speech', speech.text_to_speech),
    url(r'^scrape/scrape-text', scraper.scrape_text),
    url(r'^scrape/scrape-text-with-selector', scraper.scrape_text_with_selector),
    url(r'^twitter/update-now', twitter.post_update),
    url(r'^weather/current-temperature', weather.current_temperature),
    url(r'^weather/forecast', weather.forecast),
    url(r'^weather/radar', weather.radar),
    url(r'^image/resize', image_processing.resize),
    url(r'^blackjack/$', blackjack.createGame),
    url(r'^blackjack/(?P<game_token>[^/]+)/$', blackjack.getGame),
    url(r'^blackjack/(?P<game_token>[^/]+)/hit$', blackjack.hitGame),
    url(r'^blackjack/(?P<game_token>[^/]+)/stand$', blackjack.standGame),
]
