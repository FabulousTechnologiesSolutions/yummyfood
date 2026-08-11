from django.contrib import admin

from apps.geo.models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('id',)
