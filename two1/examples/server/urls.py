import json
import itertools
import sys

from two1.examples.server import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import os


urlpatterns = [
    url(r'^bitcoin_auth/', include('bitcoin_auth.urls'))
]


def load_package(package_json):
    package_name = package_json['package']
    package_urls = package_json.get('urls')
    package_path = package_json.get('path')
    if package_path:
        sys.path.append(package_path)
    try:
        package = __import__(package_name, fromlist=['urls'])
        urls = getattr(package, 'urls').urlpatterns
        if package_urls:
            return itertools.filterfalse(lambda u: not (u.regex.pattern in package_urls), urls)
        return urls
    except Exception as e:
        print(e)
        return []


def load_endpoints():
    ep_json = json.load(open(os.path.join(settings.BASE_DIR, 'server', settings.ENDPOINTS_FILE)))
    package_urls = list(map(lambda p: load_package(p), ep_json))
    result = [u for u in itertools.chain.from_iterable(package_urls)]
    return result


urlpatterns += load_endpoints()
urlpatterns += staticfiles_urlpatterns()
