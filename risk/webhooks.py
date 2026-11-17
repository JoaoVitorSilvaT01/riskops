import hashlib
import hmac
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from .models import OutboxEvent

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def validate_target(url):
    parsed = urllib.parse.urlparse(url)
    allow_local = os.getenv('WEBHOOK_ALLOW_LOCAL', 'false').lower() == 'true'
    if parsed.scheme not in (['http', 'https'] if allow_local else ['https']) or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Configure um webhook HTTPS sem credenciais na URL.')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    if not allow_local and any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Webhooks privados exigem WEBHOOK_ALLOW_LOCAL=true apenas no desenvolvimento.')

def deliver_pending(limit=20):
    url = os.getenv('WEBHOOK_URL', '')
    if not url: return {'delivered': 0, 'failed': 0, 'skipped': 'Webhook não configurado; eventos preservados.'}
    secret = os.getenv('WEBHOOK_SECRET', '')
    if not secret: raise ValueError('Configure WEBHOOK_SECRET antes de entregar alertas.')
    try:
        validate_target(url)
    except socket.gaierror:
        return {'delivered': 0, 'failed': 0, 'skipped': 'DNS do receptor indisponível; eventos preservados para nova tentativa.'}
    now = timezone.now()
    # Recover abandoned leases after a worker crash. Receiver deduplicates by event ID.
    OutboxEvent.objects.filter(status='processing', next_attempt_at__lte=now).update(status='pending')
    OutboxEvent.objects.filter(status='pending', attempts__gte=5).update(status='failed', last_error='Limite de tentativas atingido após retomada do worker.')
    ids = list(OutboxEvent.objects.filter(status='pending', next_attempt_at__lte=now).order_by('created_at').values_list('id', flat=True)[:limit])
    stats = {'delivered': 0, 'failed': 0}
    for event_id in ids:
        if not OutboxEvent.objects.filter(pk=event_id, status='pending').update(status='processing',
            attempts=F('attempts') + 1, next_attempt_at=now + timedelta(minutes=2)): continue
        event = OutboxEvent.objects.get(pk=event_id)
        timestamp = str(int(timezone.now().timestamp()))
        body = json.dumps({'id': str(event.id), 'type': event.event_type, 'created_at': event.created_at.isoformat(),
                           'data': event.payload}, ensure_ascii=False, separators=(',', ':')).encode()
        signature = hmac.new(secret.encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
        request = urllib.request.Request(url, data=body, method='POST', headers={'Content-Type': 'application/json',
            'X-RiskOps-Signature': 'sha256=' + signature, 'X-RiskOps-Timestamp': timestamp, 'Idempotency-Key': str(event.id)})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
                if not 200 <= response.status < 300: raise ValueError('Status HTTP não aceito.')
            event.status = 'delivered'
            event.delivered_at = timezone.now()
            event.last_error = ''
            stats['delivered'] += 1
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            event.status = 'failed' if event.attempts >= 5 else 'pending'
            event.last_error = 'Entrega não confirmada pelo destino; consulte o receptor.'
            event.next_attempt_at = timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** event.attempts))
            stats['failed'] += 1
        event.save()
    return stats
