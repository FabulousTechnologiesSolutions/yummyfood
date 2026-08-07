from django.contrib import admin

from apps.restaurants.models import (
    Deal,
    DealLine,
    MenuCategory,
    MenuItem,
    MenuItemSize,
    Restaurant,
)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'owner', 'claim_status', 'is_paused')
    search_fields = ('name', 'slug', 'primary_phone')
    list_filter = ('claim_status', 'is_paused', 'is_permanently_closed')


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'position', 'is_visible')
    list_filter = ('is_visible',)
    search_fields = ('name', 'slug')


class MenuItemSizeInline(admin.TabularInline):
    model = MenuItemSize
    extra = 0


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'restaurant', 'status', 'base_price', 'is_available')
    list_filter = ('status', 'is_available', 'is_popular')
    search_fields = ('name', 'sku')
    filter_horizontal = ('categories',)
    inlines = [MenuItemSizeInline]


class DealLineInline(admin.TabularInline):
    model = DealLine
    extra = 0


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'restaurant', 'deal_price', 'status', 'starts_at', 'ends_at')
    list_filter = ('status',)
    search_fields = ('label',)
    inlines = [DealLineInline]
