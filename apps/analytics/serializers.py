from rest_framework import serializers


class AnalyticsEventSerializer(serializers.Serializer):
    event_model = serializers.ChoiceField(choices=['item', 'deal'])
    resource_id = serializers.IntegerField(min_value=1)
    event_type = serializers.CharField(max_length=32)
