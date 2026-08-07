from rest_framework import serializers


class PresignSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120)
    byte_size = serializers.IntegerField(min_value=1)
    kind = serializers.CharField(max_length=40, required=False, allow_blank=True, default='')


class DeleteKeySerializer(serializers.Serializer):
    key = serializers.CharField(max_length=512)
