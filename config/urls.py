from django.urls import path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView
from risk import views

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html')),
    path('api/session', views.session_view),
    path('api/login', views.login_view),
    path('api/logout', views.logout_view),
    path('api/health', views.health),
    path('api/dashboard', views.dashboard),
    path('api/incidents', views.incidents),
    path('api/incidents/<uuid:incident_id>', views.incident_detail),
    path('api/incidents/<uuid:incident_id>/review', views.review),
    path('api/incidents/<uuid:incident_id>/status', views.change_status),
    path('api/incidents/<uuid:incident_id>/reanalyze', views.reanalyze),
    path('api/export', views.export_csv),
    path('api/policies', views.policies),
    path('api/integrations', views.integrations),
    path('api/evaluation', views.evaluation),
    path('api/schema', SpectacularAPIView.as_view(), name='schema'),
]
