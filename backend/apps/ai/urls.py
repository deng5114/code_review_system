from rest_framework.routers import DefaultRouter

from apps.ai.views import AIConfigViewSet

router = DefaultRouter()
router.register(r"configs", AIConfigViewSet, basename="aiconfig")

urlpatterns = router.urls
