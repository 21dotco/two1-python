"""cloudcall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url, include
from cloudcall import views, language, qr_code, speech, face_detect, phone, charts, weather, image_processing, scraper
from cloudcall.static_serve import static_serve
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    url(r'^$', views.default),
    url(r'^charts/chart', charts.chart),
    url(r'^facedetect/detect-from-url', face_detect.detect_from_url),
    url(r'^facedetect/detect-from-file', face_detect.detect_from_file),
    url(r'^facedetect/detect2-from-file', face_detect.detect2_from_file),
    url(r'^facedetect/extract-from-file', face_detect.extract_from_file),
    url(r'^language/translate', language.translate),
    url(r'^language/sentiment-analysis', language.sentiment_analysis),
    url(r'^phone/phone-lookup', phone.phone_lookup),
    url(r'^phone/send-sms', phone.send_sms),
    url(r'^qrcode/generate', qr_code.generate),
    url(r'^speech/text-to-speech', speech.text_to_speech),
    url(r'^scrape/scrape-text', scraper.scrape_text),
    url(r'^scrape/scrape-text-with-selector', scraper.scrape_text_with_selector),
    url(r'^weather/current-temperature', weather.current_temperature),
    url(r'^weather/forecast', weather.forecast),
    url(r'^weather/radar', weather.radar),
    url(r'^serve/*', static_serve.index),
	url(r'^image/resize', image_processing.resize, name='resize'),
    url(r'^docs/', include('rest_framework_swagger.urls')),
]

urlpatterns += staticfiles_urlpatterns()
