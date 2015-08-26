from django.conf.urls import url
from . import static_serve

urlpatterns = [url(r'^serve/*', static_serve.index)]


def configurator(path, parameters):
    static_serve.add_static_serve_item(path, parameters)