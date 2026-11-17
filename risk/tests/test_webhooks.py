import hashlib
import hmac
import json
import os
import socket
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from risk.models import OutboxEvent
from risk.services import create_incident
from risk.webhooks import deliver_pending, validate_target

class WebhookTests(TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'AI_PROVIDER': 'rules', 'WEBHOOK_URL': 'http://127.0.0.1:9001/alerts',
            'WEBHOOK_ALLOW_LOCAL': 'true', 'WEBHOOK_SECRET': 'test-signing-secret'})
        self.environment.start(); self.addCleanup(self.environment.stop)
        user = User.objects.create_user('demo')
        self.incident = create_incident({'title': 'Fumaça no painel', 'report': 'Há fumaça saindo do painel elétrico agora.',
            'location': 'Linha 3', 'is_synthetic': True}, user)

    def test_signed_delivery_and_idempotency_header(self):
        response = MagicMock(); response.__enter__.return_value.status = 204
        opener = MagicMock(); opener.open.return_value = response
        with patch('risk.webhooks.urllib.request.build_opener', return_value=opener):
            result = deliver_pending()
        self.assertEqual(result['delivered'], 1)
        event = OutboxEvent.objects.get()
        self.assertEqual(event.status, 'delivered')
        request = opener.open.call_args.args[0]
        timestamp = request.get_header('X-riskops-timestamp')
        expected = hmac.new(b'test-signing-secret', timestamp.encode() + b'.' + request.data, hashlib.sha256).hexdigest()
        self.assertEqual(request.get_header('X-riskops-signature'), 'sha256=' + expected)
        self.assertEqual(request.get_header('Idempotency-key'), str(event.id))
        self.assertNotIn('report', json.loads(request.data)['data'])

    def test_failed_delivery_is_retried_with_backoff(self):
        opener = MagicMock(); opener.open.side_effect = TimeoutError()
        with patch('risk.webhooks.urllib.request.build_opener', return_value=opener): result = deliver_pending()
        self.assertEqual(result['failed'], 1)
        event = OutboxEvent.objects.get()
        self.assertEqual(event.status, 'pending')
        self.assertEqual(event.attempts, 1)
        self.assertGreater(event.next_attempt_at, timezone.now())

    def test_five_attempts_end_in_failed_state(self):
        OutboxEvent.objects.update(attempts=4)
        opener = MagicMock(); opener.open.side_effect = TimeoutError()
        with patch('risk.webhooks.urllib.request.build_opener', return_value=opener): deliver_pending()
        self.assertEqual(OutboxEvent.objects.get().status, 'failed')

    def test_no_receiver_keeps_pending_events(self):
        with patch.dict(os.environ, {'WEBHOOK_URL': ''}): result = deliver_pending()
        self.assertIn('skipped', result)
        self.assertEqual(OutboxEvent.objects.get().attempts, 0)

    def test_local_receiver_is_rejected_without_explicit_development_flag(self):
        with patch.dict(os.environ, {'WEBHOOK_ALLOW_LOCAL': 'false'}):
            with self.assertRaises(ValueError): validate_target('https://127.0.0.1/alerts')

    def test_delivered_event_is_not_sent_again(self):
        OutboxEvent.objects.update(status='delivered')
        with patch('risk.webhooks.urllib.request.build_opener') as opener: deliver_pending()
        opener.assert_not_called()

    def test_dns_outage_preserves_pending_events_for_later_attempt(self):
        with patch('risk.webhooks.socket.getaddrinfo', side_effect=socket.gaierror()):
            result = deliver_pending()
        self.assertIn('skipped', result)
        self.assertEqual(OutboxEvent.objects.get().attempts, 0)

    def test_expired_lease_does_not_exceed_attempt_limit(self):
        OutboxEvent.objects.update(status='processing', attempts=5, next_attempt_at=timezone.now())
        with patch('risk.webhooks.urllib.request.build_opener') as opener:
            deliver_pending()
        opener.assert_not_called()
        self.assertEqual(OutboxEvent.objects.get().status, 'failed')
