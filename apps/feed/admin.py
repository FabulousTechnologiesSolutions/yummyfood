from django.contrib import admin

from apps.feed.models import FeedImpression, FeedViewerState


@admin.register(FeedViewerState)
class FeedViewerStateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'ip_hash',
        'promoted_rotate_offset',
        'updated_at',
    )
    search_fields = ('ip_hash',)


@admin.register(FeedImpression)
class FeedImpressionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'ip_hash',
        'menu_item',
        'deal',
        'serve_count',
        'watched_ms',
        'outcome',
        'last_served_at',
    )
    list_filter = ('outcome',)
