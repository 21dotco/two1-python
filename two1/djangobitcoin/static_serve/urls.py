from django.conf.urls import url
from . import static_serve

urlpatterns = [url(r'^serve/*', static_serve.index)]