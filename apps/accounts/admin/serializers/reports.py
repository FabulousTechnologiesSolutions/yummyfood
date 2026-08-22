from rest_framework import serializers


class ReportAdminNoteSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, default='')
