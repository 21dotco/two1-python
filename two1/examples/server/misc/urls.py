from django.conf.urls import url
from two1.examples.server.misc import phone, search


urlpatterns = [
    url(r'^phone/send-sms$', phone.send_sms),
    url(r'^search/bing$', search.bing)
]


def configurator(path, parameters):
    pass
