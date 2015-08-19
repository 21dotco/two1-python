from django.conf.urls import url
from static_serve import static_serve

urlpatterns = [url(r'^serve/*', static_serve.index)]