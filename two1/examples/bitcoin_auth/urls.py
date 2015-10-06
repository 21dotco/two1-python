"""urls for bitcoin_auth."""

from django.conf.urls import url
import bitcoin_auth.views as views

urlpatterns = [
    url(r'^token$', views.token)
]
