from rest_framework import serializers
from .models import Incident, PRIORITIES, STATUSES

class IncidentInput(serializers.Serializer):
    title = serializers.CharField(min_length=5, max_length=160)
    report = serializers.CharField(min_length=20, max_length=6000)
    location = serializers.CharField(min_length=2, max_length=160)
    reporter = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    is_synthetic = serializers.BooleanField(default=True)

class ReviewInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    priority = serializers.ChoiceField(choices=PRIORITIES)
    reason = serializers.CharField(min_length=12, max_length=2000)
    assigned_to = serializers.CharField(min_length=2, max_length=100)

class StatusInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=STATUSES)
    reason = serializers.CharField(min_length=12, max_length=2000)

class ReanalysisInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)

class IncidentOutput(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = ['id', 'title', 'report', 'location', 'reporter', 'category', 'priority', 'status',
                  'analysis', 'analysis_status', 'analysis_error', 'reviewed_priority', 'assigned_to', 'version', 'is_synthetic', 'created_at', 'updated_at']

class LoginInput(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=256, write_only=True, trim_whitespace=False)

class IncidentListOutput(serializers.Serializer):
    count = serializers.IntegerField()
    results = IncidentOutput(many=True)
    next_offset = serializers.IntegerField(allow_null=True)

class IncidentDetailOutput(IncidentOutput):
    audit = serializers.ListField(child=serializers.JSONField())
    audit_valid = serializers.BooleanField()
    alerts = serializers.ListField(child=serializers.JSONField())
    class Meta(IncidentOutput.Meta):
        fields = IncidentOutput.Meta.fields + ['audit', 'audit_valid', 'alerts']
