from django.contrib import admin
from django.urls import path
from safarank import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('', views.login_usuario, name='login'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('logout/', views.logout_usuario, name='logout'),

    # NUEVA ESTRUCTURA
    path('dashboard/', views.dashboard, name='dashboard'),  # Nuevo Menú Principal
    path('catalogo/', views.catalogo, name='catalogo'),  # Antes era 'inicio'

    path('movil/<int:movil_id>/', views.detalle_movil, name='detalle_movil'),

    # Rankings
    path('mis-rankings/', views.mis_rankings, name='mis_rankings'),
    path('ranking/<int:ranking_id>/', views.ver_ranking, name='ver_ranking'),
    path('ranking/borrar/<int:ranking_id>/', views.borrar_ranking, name='borrar_ranking'),

    # NUEVO: Ruta para guardar el orden del ranking (AJAX)
    path('ranking/guardar-orden/', views.guardar_orden_ranking, name='guardar_orden_ranking'),

    # Admin
    path('panel-admin/', views.panel_administracion, name='panel_administracion'),
    path('cargar-datos/', views.cargar_datos, name='cargar_datos'),
path('estadisticas/', views.estadisticas, name='estadisticas'),
]