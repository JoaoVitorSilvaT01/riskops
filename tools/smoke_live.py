"""Opt-in live integration test. Uses the configured provider and consumes API quota.

Server must already be running. Creates one synthetic occurrence and tests the workflow.
Run: python tools/smoke_live.py
"""
import http.cookiejar
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')
BASE = os.getenv('SMOKE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')

def main():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = ''

    def request(path, data=None, expected=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data is not None else None
        req = urllib.request.Request(BASE + '/api/' + path, data=body,
            headers={'Content-Type': 'application/json', 'X-CSRFToken': token})
        try:
            response = opener.open(req, timeout=75)
            status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        result = json.loads(raw)
        if status != expected:
            raise RuntimeError(f'{path}: HTTP {status} (esperado {expected}): {result.get("detail", "erro de validação")}')
        return result

    session = request('session'); token = session['csrf_token']
    credentials = request('login', {'username': os.getenv('SMOKE_USERNAME', 'demo'),
                                   'password': os.getenv('DEMO_PASSWORD', 'demo-local-2026')})
    token = credentials['csrf_token']
    dashboard = request('dashboard')
    if dashboard['provider']['provider'] != 'gemini' or not dashboard['provider']['configured']:
        raise RuntimeError('O servidor precisa estar configurado com Gemini e chave válida para este teste.')
    report = 'Há fumaça saindo do painel elétrico da linha 3 agora durante a operação. A exposição de pessoas ainda precisa ser confirmada.'
    incident = request('incidents', {'title': 'Teste Gemini · ' + uuid.uuid4().hex[:8],
        'report': report, 'location': 'Laboratório de demonstração · Linha 03',
        'reporter': 'Teste automatizado sintético', 'is_synthetic': True}, expected=201)
    analysis = incident['analysis']
    assert analysis['is_llm'] and analysis['provider'] == 'gemini', 'Análise precisa vir do Gemini real.'
    assert incident['priority'] == 'P1', 'A emergência sintética deve receber prioridade P1.'
    assert analysis['evidence'] and all(e in report for e in analysis['evidence']), 'Evidência deve ser literal.'
    path = 'incidents/' + incident['id']
    assert incident['analysis_status'] == 'completed', incident.get('analysis_error')
    review = {'expected_version': incident['version'], 'priority': 'P1', 'assigned_to': 'Equipe de teste local',
              'reason': 'Cenário sintético validado no teste de integração real com Gemini.'}
    reviewed = request(path + '/review', review)
    assert reviewed['version'] == incident['version'] + 1 and reviewed['reviewed_priority'] == 'P1'
    request(path + '/review', review, expected=409)
    resolved = request(path + '/status', {'expected_version': reviewed['version'], 'status': 'resolved',
        'reason': 'Teste sintético concluído; sem ocorrência real ou intervenção operacional.'})
    assert resolved['version'] == reviewed['version'] + 1
    detail = request(path)
    assert detail['audit_valid'] and len(detail['audit']) == 4
    assert len(detail['alerts']) == 1, 'P1 precisa gerar um evento persistente de alerta.'
    print(json.dumps({'ok': True, 'incident_id': incident['id'], 'provider': analysis['provider'],
        'model': analysis['model'], 'latency_ms': analysis['latency_ms'], 'priority': incident['priority'],
        'checks': ['session_and_csrf', 'real_gemini_analysis', 'literal_evidence', 'human_review',
                   'stale_version_409', 'resolution', 'audit_chain', 'outbox_event']}, ensure_ascii=True))

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, AssertionError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True))
        raise SystemExit(1) from None
