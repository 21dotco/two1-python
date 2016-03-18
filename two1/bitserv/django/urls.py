"""Added URLs for a bitserv server."""
from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from .views import ChannelViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'channel/?', ChannelViewSet, 'Channel')
urlpatterns = router.urls
