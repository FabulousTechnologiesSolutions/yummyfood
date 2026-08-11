from django.contrib import admin

from apps.engagement.models import SavedItem


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'target_type', 'menu_item', 'deal', 'created_at')
    list_filter = ('target_type',)
    search_fields = ('user__phone_number',)
    raw_id_fields = ('user', 'menu_item', 'deal')
    ordering = ('-created_at',)
