import csv
import json
import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import exception_handler as drf_exception_handler
from .models import Incident, OutboxEvent
from .policies import POLICIES, POLICY_VERSION
from .providers import ProviderError, provider_info
from .serializers import IncidentInput, IncidentOutput, IncidentListOutput, IncidentDetailOutput, LoginInput, ReanalysisInput, ReviewInput, StatusInput
from .services import Conflict, create_incident, reanalyze_incident, review_incident, transition, verify_chain

def exception_handler(exc, context):
    if isinstance(exc, ProviderError): return Response({'detail': str(exc), 'code': 'provider_error'}, status=502)
    if isinstance(exc, Conflict): return Response({'detail': str(exc), 'code': 'version_conflict'}, status=409)
    return drf_exception_handler(exc, context)

@ensure_csrf_cookie
@require_http_methods(['GET'])
def session_view(request):
    return JsonResponse({'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'csrf_token': get_token(request), 'can_review': request.user.has_perm('risk.change_incident'), 'debug': settings.DEBUG})

@csrf_protect
@require_http_methods(['POST'])
def login_view(request):
    # CSRF-protected even before a session is authenticated.
    if len(request.body) > 4096: return JsonResponse({'detail': 'Requisição muito grande.'}, status=400)
    try: data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError): return JsonResponse({'detail': 'JSON inválido.'}, status=400)
    serializer = LoginInput(data=data)
    if not serializer.is_valid(): return JsonResponse(serializer.errors, status=400)
    from django.core.cache import cache
    key = 'login:' + request.META.get('REMOTE_ADDR', '')
    attempts = cache.get(key, 0)
    if attempts >= 10: return JsonResponse({'detail': 'Muitas tentativas. Aguarde um minuto.'}, status=429)
    user = authenticate(request, **serializer.validated_data)
    if user is None:
        cache.set(key, attempts + 1, timeout=60)
        return JsonResponse({'detail': 'Usuário ou senha inválidos.'}, status=401)
    cache.delete(key)
    login(request, user)
    return JsonResponse({'username': user.username, 'csrf_token': get_token(request)})

@csrf_protect
@require_http_methods(['POST'])
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True})

@require_http_methods(['GET'])
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'riskops'})

def validated(cls, request):
    serializer = cls(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data

def require_reviewer(request):
    from rest_framework.exceptions import PermissionDenied
    if not request.user.has_perm('risk.change_incident'):
        raise PermissionDenied('A revisão exige permissão de responsável.')

class AnalysisThrottle(UserRateThrottle):
    scope = 'analysis'

@extend_schema(methods=['GET'], operation_id='incidents_list', responses=IncidentListOutput, parameters=[
    OpenApiParameter('priority', str), OpenApiParameter('status', str), OpenApiParameter('category', str),
    OpenApiParameter('q', str), OpenApiParameter('offset', int), OpenApiParameter('open', bool)])
@extend_schema(methods=['POST'], request=IncidentInput, responses={201: IncidentOutput})
@api_view(['GET', 'POST'])
@throttle_classes([AnalysisThrottle])
def incidents(request):
    if request.method == 'POST':
        incident = create_incident(validated(IncidentInput, request), request.user)
        return Response(IncidentOutput(incident).data, status=201)
    qs = Incident.objects.all()
    if request.query_params.get('open', '').lower() == 'true': qs = qs.exclude(status='resolved')
    for key in ['priority', 'status', 'category']:
        if request.query_params.get(key): qs = qs.filter(**{key: request.query_params[key]})
    search = request.query_params.get('q', '')[:160]
    if search: qs = qs.filter(Q(title__icontains=search) | Q(report__icontains=search) | Q(location__icontains=search))
    count = qs.count()
    try: offset = max(0, int(request.query_params.get('offset', '0')))
    except ValueError: offset = 0
    return Response({'count': count, 'results': IncidentOutput(qs[offset:offset + 50], many=True).data,
                     'next_offset': offset + 50 if offset + 50 < count else None})

@extend_schema(responses=IncidentDetailOutput)
@api_view(['GET'])
def incident_detail(request, incident_id):
    incident = get_object_or_404(Incident, pk=incident_id)
    return Response({**IncidentOutput(incident).data,
        'audit': list(incident.events.values('id', 'actor', 'action', 'payload', 'created_at', 'event_hash', 'previous_hash')),
        'audit_valid': verify_chain(incident),
        'alerts': list(OutboxEvent.objects.filter(incident=incident).values('id', 'status', 'attempts', 'last_error', 'delivered_at'))})

@extend_schema(request=ReviewInput, responses=IncidentOutput)
@api_view(['POST'])
def review(request, incident_id):
    require_reviewer(request)
    get_object_or_404(Incident, pk=incident_id)
    incident = review_incident(incident_id, validated(ReviewInput, request), request.user)
    return Response(IncidentOutput(incident).data)

@extend_schema(request=StatusInput, responses=IncidentOutput)
@api_view(['POST'])
def change_status(request, incident_id):
    require_reviewer(request)
    get_object_or_404(Incident, pk=incident_id)
    return Response(IncidentOutput(transition(incident_id, validated(StatusInput, request), request.user)).data)

@extend_schema(request=ReanalysisInput, responses=IncidentOutput)
@api_view(['POST'])
@throttle_classes([AnalysisThrottle])
def reanalyze(request, incident_id):
    require_reviewer(request)
    get_object_or_404(Incident, pk=incident_id)
    data = validated(ReanalysisInput, request)
    return Response(IncidentOutput(reanalyze_incident(incident_id, data['expected_version'], request.user)).data)

@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
def dashboard(request):
    qs = Incident.objects.all()
    count = qs.count()
    reviewed = qs.exclude(reviewed_priority='').count()
    analyses = qs.values_list('analysis', flat=True)
    times = [a.get('latency_ms', 0) for a in analyses]
    return Response({'total': count, 'open': qs.exclude(status='resolved').count(),
        'urgent': qs.filter(priority='P1').exclude(status='resolved').count(),
        'awaiting_review': qs.filter(reviewed_priority='').exclude(status='resolved').count(),
        'reviewed': reviewed, 'review_rate': round(reviewed / count * 100) if count else 0,
        'average_latency_ms': round(sum(times) / len(times)) if times else 0,
        'categories': list(qs.values('category').annotate(count=Count('id')).order_by('-count')),
        'priorities': {p: qs.filter(priority=p).exclude(status='resolved').count() for p in ['P1', 'P2', 'P3', 'P4']},
        'outbox': {s: OutboxEvent.objects.filter(status=s).count() for s in ['pending', 'processing', 'delivered', 'failed']},
        'provider': provider_info(), 'synthetic_count': qs.filter(is_synthetic=True).count(), 'policy_version': POLICY_VERSION})

@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
def policies(request):
    return Response({'version': POLICY_VERSION, 'notice': 'Procedimentos fictícios para demonstração; sem validade normativa.', 'items': POLICIES})

@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
def integrations(request):
    return Response({'provider': provider_info(), 'webhook_configured': bool(os.getenv('WEBHOOK_URL')),
        'webhook_signed': bool(os.getenv('WEBHOOK_SECRET')),
        'events': list(OutboxEvent.objects.values('id', 'incident_id', 'event_type', 'status', 'attempts', 'last_error',
                                                'created_at', 'delivered_at')[:50])})

@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
def evaluation(request):
    path = Path(settings.BASE_DIR) / 'evaluation' / 'results.json'
    if not path.exists(): return Response({'available': False})
    try: result = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError): return Response({'available': False})
    return Response({'available': True, **result})

def csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text

@extend_schema(responses={(200, 'text/csv'): OpenApiTypes.STR})
@api_view(['GET'])
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="riskops-ocorrencias.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['id', 'titulo', 'local', 'categoria', 'prioridade', 'status', 'responsavel', 'sintetico', 'criado_em'])
    for row in Incident.objects.values_list('id', 'title', 'location', 'category', 'priority', 'status', 'assigned_to', 'is_synthetic', 'created_at').iterator():
        writer.writerow([csv_safe(v) for v in row])
    return response
