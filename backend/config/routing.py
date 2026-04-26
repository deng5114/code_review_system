from django.urls import re_path

from apps.reviews.consumers import ReviewProgressConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/reviews/(?P<review_id>[\w-]+)/progress/$",
        ReviewProgressConsumer.as_asgi(),
    ),
]
