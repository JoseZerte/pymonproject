from django.contrib import admin
from django.urls import path
from safarank import views

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin de Django (opcional si usas el tuyo propio)

    # Auth
    path('', views.login_usuario, name='login'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('logout/', views.logout_usuario, name='logout'),

    # Principal
    path('inicio/', views.inicio, name='inicio'),

    # Nuevas funcionalidades
    path('movil/<int:movil_id>/', views.detalle_movil, name='detalle_movil'),
    path('mis-rankings/', views.mis_rankings, name='mis_rankings'),

    # Administración Custom
    path('panel-admin/', views.panel_administracion, name='panel_administracion'),
    path('cargar-datos/', views.cargar_datos, name='cargar_datos'),
]