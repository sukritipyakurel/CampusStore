from django.conf import settings

from .models import Category


def store_globals(request):
    return {
        "nav_categories": Category.objects.all(),
        "STORE_NAME": settings.STORE_NAME,
        "GOOGLE_ANALYTICS_ID": settings.GOOGLE_ANALYTICS_ID,
        "FACEBOOK_PIXEL_ID": settings.FACEBOOK_PIXEL_ID,
        "TWITTER_PIXEL_ID": settings.TWITTER_PIXEL_ID,
    }
