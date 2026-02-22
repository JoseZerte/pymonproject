from django.contrib import admin
from django.urls import path
from safarank import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('', views.login_usuario, name='login'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('logout/', views.logout_usuario, name='logout'),


    path('dashboard/', views.dashboard, name='dashboard'),  # Nuevo Menú Principal
    path('catalogo/', views.catalogo, name='catalogo'),  # Antes era 'inicio'

    path('movil/<int:movil_id>/', views.detalle_movil, name='detalle_movil'),

    # Rankings
    path('mis-rankings/', views.mis_rankings, name='mis_rankings'),
    path('ranking/<int:ranking_id>/', views.ver_ranking, name='ver_ranking'),
    path('ranking/borrar/<int:ranking_id>/', views.borrar_ranking, name='borrar_ranking'),


    path('ranking/guardar-orden/', views.guardar_orden_ranking, name='guardar_orden_ranking'),

    # Admin
    path('panel-admin/', views.panel_administracion, name='panel_administracion'),
    path('cargar-datos/', views.cargar_datos, name='cargar_datos'),


    path('gestion/elementos/', views.admin_catalogo, name='admin_catalogo'),
    path('gestion/elementos/crear/', views.crear_movil, name='crear_movil'),
    path('gestion/elementos/editar/<int:movil_id>/', views.editar_movil, name='editar_movil'),
    path('gestion/elementos/borrar/<int:movil_id>/', views.borrar_movil, name='borrar_movil'),

    path('gestion/categorias/', views.admin_categorias, name='admin_categorias'),
    path('gestion/categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('gestion/categorias/editar/<int:cat_id>/', views.editar_categoria, name='editar_categoria'),
    path('gestion/categorias/borrar/<int:cat_id>/', views.borrar_categoria, name='borrar_categoria'),

    path('panel-admin/estadisticas/', views.estadisticas_globales, name='estadisticas_globales'),
]

