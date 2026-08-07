from rest_framework import serializers

from apps.restaurants.models import DealStatus, ItemType, MenuItemStatus


class MediaInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    type = serializers.ChoiceField(choices=['image', 'video'])
    url = serializers.CharField(required=False, allow_blank=True, default='')
    is_cover = serializers.BooleanField(required=False, default=False)


class SizeInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=40)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    offer_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    position = serializers.IntegerField(required=False, min_value=0)


class CategoryCreateSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=64)
    name = serializers.CharField(max_length=120)
    icon = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(required=False, min_value=0, default=0)
    is_visible = serializers.BooleanField(required=False, default=True)


class CategoryUpdateSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=64, required=False)
    name = serializers.CharField(max_length=120, required=False)
    icon = serializers.CharField(max_length=32, required=False, allow_blank=True)
    position = serializers.IntegerField(required=False, min_value=0)
    is_visible = serializers.BooleanField(required=False)


class CategoryReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class MenuItemCreateSerializer(serializers.Serializer):
    category_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    subcategory = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')
    item_type = serializers.ChoiceField(
        choices=ItemType.choices, required=False, allow_blank=True, default=''
    )
    quantity_label = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')
    sku = serializers.CharField(max_length=40, required=False, allow_blank=True, default='')
    is_available = serializers.BooleanField(required=False, default=True)
    is_popular = serializers.BooleanField(required=False, default=False)
    is_new = serializers.BooleanField(required=False, default=False)
    spicy_level = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=3)
    prep_time_min = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    calories = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    emoji = serializers.CharField(max_length=16, required=False, allow_blank=True, default='')
    sizes = SizeInputSerializer(many=True)
    media = MediaInputSerializer(many=True)


class MenuItemUpdateSerializer(serializers.Serializer):
    category_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    name = serializers.CharField(max_length=120, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    subcategory = serializers.CharField(max_length=80, required=False, allow_blank=True)
    item_type = serializers.ChoiceField(
        choices=ItemType.choices, required=False, allow_blank=True
    )
    quantity_label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    sku = serializers.CharField(max_length=40, required=False, allow_blank=True)
    is_available = serializers.BooleanField(required=False)
    is_popular = serializers.BooleanField(required=False)
    is_new = serializers.BooleanField(required=False)
    spicy_level = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=3)
    prep_time_min = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    calories = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    emoji = serializers.CharField(max_length=16, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=MenuItemStatus.choices, required=False)
    sizes = SizeInputSerializer(many=True, required=False)
    media = MediaInputSerializer(many=True, required=False)


class MoveMenuItemSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(min_value=1)


class AvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class DealLineInputSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField(min_value=1)
    size_label = serializers.CharField(max_length=40)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    position = serializers.IntegerField(required=False, min_value=0)


class DealCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    deal_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        default=list,
    )
    terms = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=DealStatus.choices, required=False)
    lines = DealLineInputSerializer(many=True)
    media = MediaInputSerializer(many=True)


class DealUpdateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    deal_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False)
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
    )
    terms = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=DealStatus.choices, required=False)
    lines = DealLineInputSerializer(many=True, required=False)
    media = MediaInputSerializer(many=True, required=False)
