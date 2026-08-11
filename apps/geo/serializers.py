from rest_framework import serializers

from apps.geo.models import City


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'name', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CityPickerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    restaurant_count = serializers.IntegerField()
