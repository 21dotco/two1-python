"""urls for bitcoin_auth."""

from django.conf.urls import url, include
import bitcoin_auth.views as views
from rest_framework.routers import DefaultRouter

# Create a router with our viewsets
router = DefaultRouter()
router.register(r'payment', views.ChannelViewSet, 'Channel')

urlpatterns = [
    url(r'^token$', views.token),
    url(r'', include(router.urls))
]
