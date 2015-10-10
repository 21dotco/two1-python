"""Routes to reach Payment Channel APIs."""

from django.conf.urls import url, include
from . import views

urlpatterns = [
    url(r'^/?$', views.Handshake.as_view()),
    url(r'^/(?P<deposit_tx_id>\w+)/?$', views.Channel.as_view()),
]
