import hashlib
import json
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import AuditEvent, Incident, OutboxEvent
from .providers import analyze, provider_info, ProviderError, PROMPT_VERSION
from .policies import POLICY_VERSION

class Conflict(Exception):
    pass

def digest(incident_id, actor, action, payload, previous):
    return hashlib.sha256(json.dumps({'incident': str(incident_id), 'actor': actor, 'action': action,
        'payload': payload, 'previous_hash': previous}, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def audit(incident, actor, action, payload):
    previous = incident.events.order_by('-id').first()
    previous_hash = previous.event_hash if previous else ''
    return AuditEvent.objects.create(incident=incident, actor=actor, action=action, payload=payload,
        previous_hash=previous_hash, event_hash=digest(incident.id, actor, action, payload, previous_hash))

def verify_chain(incident):
    previous = ''
    for event in incident.events.all():
        if event.previous_hash != previous or event.event_hash != digest(incident.id, event.actor, event.action, event.payload, previous):
            return False
        previous = event.event_hash
    return True

def queue_alert(incident, source):
    if incident.priority != 'P1': return
    OutboxEvent.objects.create(incident=incident, next_attempt_at=timezone.now(), payload={
        'incident_id': str(incident.id), 'priority': incident.priority,
        'location': incident.location, 'source': source, 'is_synthetic': incident.is_synthetic,
        'message': 'Ocorrência prioritária aguardando avaliação humana. Consulte o sistema.',
    })

def pending_analysis():
    info = provider_info()
    return {**info, 'is_llm': False, 'category': 'indefinido', 'potential_severity': 'indeterminada',
        'suggested_priority': 'P2', 'effective_priority': 'P2', 'rule_priority': None,
        'summary': 'Relato preservado. A análise automática ainda não foi concluída; revisão manual disponível.',
        'hazards': [], 'evidence': [], 'missing_information': ['Confirmar perigo, exposição e controles com o responsável.'],
        'recommended_actions': ['Encaminhar para revisão humana; não aguardar a IA para iniciar a avaliação.'],
        'policy_ids': [], 'retrieved_policies': [], 'requires_review': True, 'latency_ms': 0,
        'flags': ['P2 é uma prioridade provisória de triagem, sem classificação automática validada.'],
        'policy_version': POLICY_VERSION, 'prompt_version': PROMPT_VERSION,
        'notice': 'Protótipo demonstrativo. A ausência de análise automática não indica ausência de perigo.'}

def complete_analysis(incident_id, report, user):
    # Intake is committed before external I/O. A process crash leaves a visible pending record.
    try:
        result, error = analyze(report), ''
    except ProviderError as exc:
        result, error = None, str(exc)[:500]
    with transaction.atomic():
        # Serialize against reviews, then inspect the latest human decision under the write lock.
        Incident.objects.filter(pk=incident_id).update(version=F('version') + 1)
        incident = Incident.objects.get(pk=incident_id)
        previous = incident.priority
        if result is not None:
            if incident.reviewed_priority:
                result['flags'].append('Análise recebida após a revisão; a prioridade confirmada pela pessoa foi preservada.')
            else:
                incident.priority = result['effective_priority']
            incident.category = result['category']
            incident.analysis = result
        incident.analysis_status = 'failed' if error else 'completed'
        incident.analysis_error = error
        incident.save()
        audit(incident, user.username, 'analysis_failed' if error else 'analysis_completed',
            {'version': incident.version, 'error': error} if error else {'version': incident.version, 'analysis': result})
        if result is not None and previous != 'P1': queue_alert(incident, 'analysis')
    return incident

def create_incident(data, user):
    with transaction.atomic():
        incident = Incident.objects.create(**data, created_by=user, analysis=pending_analysis(),
            analysis_status='pending', category='indefinido', priority='P2')
        audit(incident, user.username, 'created', {'version': 1, 'analysis_status': 'pending',
            'report_sha256': hashlib.sha256(data['report'].encode()).hexdigest()})
    return complete_analysis(incident.id, data['report'], user)

def acquire(incident_id, expected_version):
    # Compare-and-swap works on SQLite too, where select_for_update is a no-op.
    changed = Incident.objects.filter(pk=incident_id, version=expected_version).update(version=F('version') + 1)
    if not changed: raise Conflict('A ocorrência foi atualizada por outra pessoa. Recarregue os dados antes de salvar.')
    return Incident.objects.get(pk=incident_id)

def review_incident(incident_id, data, user):
    with transaction.atomic():
        incident = acquire(incident_id, data['expected_version'])
        if incident.status == 'resolved': raise Conflict('Reabra a ocorrência antes de revisar.')
        previous_priority = incident.priority
        incident.priority = data['priority']
        incident.reviewed_priority = data['priority']
        incident.assigned_to = data['assigned_to']
        incident.status = 'in_review'
        incident.save()
        audit(incident, user.username, 'reviewed', {'priority_before': previous_priority,
            'priority_after': incident.priority, 'reason': data['reason'], 'assigned_to': incident.assigned_to,
            'version': incident.version})
        if previous_priority != 'P1': queue_alert(incident, 'human_review')
    return incident

def transition(incident_id, data, user):
    with transaction.atomic():
        incident = acquire(incident_id, data['expected_version'])
        target = data['status']
        allowed = {'pending': {'in_review'}, 'in_review': {'pending', 'resolved'}, 'resolved': {'pending'}}
        if target not in allowed[incident.status]: raise Conflict('Transição de status inválida.')
        if target == 'resolved' and not incident.reviewed_priority:
            raise Conflict('Confirme a prioridade na revisão humana antes de concluir.')
        previous = incident.status
        incident.status = target
        if target == 'pending': incident.reviewed_priority = ''
        incident.save()
        audit(incident, user.username, 'status_changed', {'from': previous, 'to': target,
            'reason': data['reason'], 'version': incident.version})
    return incident

def reanalyze_incident(incident_id, expected_version, user):
    with transaction.atomic():
        incident = acquire(incident_id, expected_version)
        if incident.status == 'resolved': raise Conflict('Reabra a ocorrência antes de analisar novamente.')
        if incident.analysis_status == 'pending': raise Conflict('Uma análise já está em andamento para esta ocorrência.')
        incident.analysis_status = 'pending'
        incident.analysis_error = ''
        incident.reviewed_priority = ''
        incident.status = 'pending'
        incident.save()
        audit(incident, user.username, 'analysis_requested', {'version': incident.version})
    return complete_analysis(incident.id, incident.report, user)
