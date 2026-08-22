from django.utils.text import slugify
from rest_framework import serializers


class AdminCategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    slug = serializers.SlugField(max_length=64, required=False, allow_blank=True)
    icon = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(required=False, min_value=0, default=0)
    is_visible = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        slug = (attrs.get('slug') or '').strip().lower()
        if not slug:
            slug = slugify(attrs['name'])[:64]
        if not slug:
            raise serializers.ValidationError(
                {'slug': 'Could not generate a slug from name; provide slug explicitly.'}
            )
        attrs['slug'] = slug
        return attrs
