import uuid
from django.conf import settings
from django.db import models

PRIORITIES = [('P1', 'Urgente'), ('P2', 'Alta'), ('P3', 'Moderada'), ('P4', 'Rotina')]
STATUSES = [('pending', 'Aguardando revisão'), ('in_review', 'Em atendimento'), ('resolved', 'Concluída')]

class Incident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    report = models.TextField(max_length=6000)
    location = models.CharField(max_length=160)
    reporter = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=40, default='indefinido')
    priority = models.CharField(max_length=2, choices=PRIORITIES, default='P2')
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    analysis = models.JSONField(default=dict)
    analysis_status = models.CharField(max_length=12, default='completed', choices=[
        ('pending', 'Análise pendente'), ('completed', 'Análise concluída'), ('failed', 'Análise indisponível')])
    analysis_error = models.CharField(max_length=500, blank=True)
    reviewed_priority = models.CharField(max_length=2, choices=PRIORITIES, blank=True)
    assigned_to = models.CharField(max_length=100, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_synthetic = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', '-created_at']
        indexes = [models.Index(fields=['status', 'priority'])]

class AuditEvent(models.Model):
    incident = models.ForeignKey(Incident, related_name='events', on_delete=models.PROTECT)
    actor = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    previous_hash = models.CharField(max_length=64, blank=True)
    event_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.PROTECT)
    event_type = models.CharField(max_length=50, default='incident.priority_alert')
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=15, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    last_error = models.CharField(max_length=200, blank=True)
    delivered_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
