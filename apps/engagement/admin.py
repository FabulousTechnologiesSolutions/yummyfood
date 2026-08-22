from django.contrib import admin

from apps.engagement.models import ContentReport, Rating, SavedItem


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'target_type', 'menu_item', 'deal', 'created_at')
    list_filter = ('target_type',)
    search_fields = ('user__phone_number',)
    raw_id_fields = ('user', 'menu_item', 'deal')
    ordering = ('-created_at',)


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_by',
        'target_type',
        'restaurant',
        'menu_item',
        'deal',
        'reason',
        'status',
        'created_at',
    )
    list_filter = ('status', 'target_type', 'reason')
    search_fields = ('created_by__phone_number', 'description', 'restaurant__name')
    raw_id_fields = ('created_by', 'restaurant', 'menu_item', 'deal', 'reviewed_by')
    ordering = ('-created_at',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'target_type', 'restaurant', 'menu_item', 'deal', 'stars', 'rated_at')
    list_filter = ('target_type', 'stars')
    search_fields = ('user__phone_number', 'restaurant__name', 'description')
    raw_id_fields = ('user', 'restaurant', 'menu_item', 'deal')
    ordering = ('-rated_at',)
