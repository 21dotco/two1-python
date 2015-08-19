import json
import itertools
from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from djangobitcoin import views
import os

urlpatterns = [
    url(r'^$', views.default),
    url(r'^docs/', include('rest_framework_swagger.urls')),
]


def load_package(package_json):
    package_name = package_json['package']
    package_urls = package_json.get('urls')
    try:
        package = __import__(package_name, fromlist=['urls'])
        urls = getattr(package, 'urls').urlpatterns
        if package_urls:
            return itertools.filterfalse(lambda u: not (u.regex.pattern in package_urls), urls)
        return urls
    except:
        return []


def load_endpoints():
    ep_json = json.load(open(os.path.join(settings.BASE_DIR, 'djangobitcoin', settings.ENDPOINTS_FILE)))
    package_urls = list(map(lambda p: load_package(p), ep_json))
    result = [u for u in itertools.chain.from_iterable(package_urls)]
    return result


urlpatterns += load_endpoints()

urlpatterns += staticfiles_urlpatterns()
