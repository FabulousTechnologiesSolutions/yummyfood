from django.contrib import admin

from apps.discovery.models import ExploreImpression, ExploreViewerState

admin.site.register(ExploreViewerState)
admin.site.register(ExploreImpression)
