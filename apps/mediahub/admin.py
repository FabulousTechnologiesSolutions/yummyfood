from django.contrib import admin

from apps.mediahub.models import ContentMedia


@admin.register(ContentMedia)
class ContentMediaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'restaurant',
        'entity_type',
        'media_type',
        'is_cover',
        'processing_status',
        'created_at',
    )
    list_filter = ('entity_type', 'media_type', 'processing_status', 'is_cover')
    search_fields = ('id', 'file')
