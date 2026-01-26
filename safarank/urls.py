from django.urls import path
from . import views # Importamos tus vistas de login/registro

urlpatterns = [
    # Si quieres que la página principal sea el login, deja la ruta vacía ''
    path('', views.login_usuario, name='login'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('logout/', views.logout_usuario, name='logout'),
    # Esta es la página a la que irá el usuario tras loguearse (el ranking)
    path('inicio/', views.inicio, name='inicio'),
]