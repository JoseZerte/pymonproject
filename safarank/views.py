import csv
import io
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

# Importamos los modelos y formularios
from .forms import RegistroForm, LoginForm, ValoracionForm, RankingForm
from .models import Usuario, MovilXiaomi, Valoracion, RankingPersonal


# --- AUTENTICACIÓN ---

def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            messages.success(request, 'Usuario registrado con éxito.')
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registro.html', {'form': form})


def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, email=email, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('inicio')
            else:
                messages.error(request, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_usuario(request):
    logout(request)
    return redirect('login')


# --- VISTAS PRINCIPALES ---

@login_required(login_url='login')
def inicio(request):
    # Traemos todos los móviles de MongoDB
    moviles = MovilXiaomi.objects.using('mongodb').all()

    return render(request, 'inicio.html', {
        'nombre_usuario': request.user.nombre,
        'rol_usuario': request.user.rol,
        'moviles': moviles
    })


@login_required(login_url='login')
def detalle_movil(request, movil_id):
    """
    Muestra la ficha de un móvil, permite votar y ver comentarios.
    """
    # 1. Obtenemos el móvil específico de MongoDB
    try:
        movil = MovilXiaomi.objects.using('mongodb').get(id=movil_id)
    except MovilXiaomi.DoesNotExist:
        messages.error(request, "El móvil no existe.")
        return redirect('inicio')

    # 2. Verificamos si el usuario ya ha votado este móvil
    ya_votado = Valoracion.objects.using('mongodb').filter(
        user_email=request.user.email,
        movil_id=movil_id
    ).exists()

    # 3. Procesar formulario de votación
    if request.method == 'POST':
        if ya_votado:
            messages.warning(request, "Ya has valorado este móvil anteriormente.")
        else:
            form = ValoracionForm(request.POST)
            if form.is_valid():
                valoracion = form.save(commit=False)
                # Conectamos SQLite (email) con Mongo
                valoracion.user_email = request.user.email
                valoracion.movil_id = movil_id
                valoracion.fecha = timezone.now()
                valoracion.save(using='mongodb')

                messages.success(request, "¡Tu valoración ha sido guardada!")
                # Recargamos la página para ver el comentario nuevo
                return redirect('detalle_movil', movil_id=movil_id)
    else:
        form = ValoracionForm()

    # 4. Obtener todas las valoraciones de este móvil
    valoraciones = Valoracion.objects.using('mongodb').filter(movil_id=movil_id).order_by('-fecha')

    return render(request, 'detalle_movil.html', {
        'movil': movil,
        'form': form,
        'ya_votado': ya_votado,
        'valoraciones': valoraciones
    })


@login_required(login_url='login')
def mis_rankings(request):
    """
    Muestra los rankings creados por el usuario y permite crear nuevos.
    """
    # Obtener rankings del usuario actual desde MongoDB
    rankings = RankingPersonal.objects.using('mongodb').filter(user_email=request.user.email)

    if request.method == 'POST':
        form = RankingForm(request.POST)
        if form.is_valid():
            nuevo_ranking = form.save(commit=False)
            nuevo_ranking.user_email = request.user.email
            nuevo_ranking.save(using='mongodb')
            messages.success(request, f"Ranking '{nuevo_ranking.nombre}' creado.")
            return redirect('mis_rankings')
    else:
        form = RankingForm()

    return render(request, 'mis_rankings.html', {
        'rankings': rankings,
        'form': form
    })


# --- VISTAS DE ADMINISTRACIÓN ---

@login_required(login_url='login')
def panel_administracion(request):
    if request.user.rol != 'admin':
        messages.error(request, "Acceso no autorizado.")
        return redirect('inicio')
    return render(request, 'admin.html')


@login_required(login_url='login')
def cargar_datos(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == "POST":
        uploaded_file = request.FILES.get('csvFile')

        if not uploaded_file:
            return render(request, 'data_load.html', {'error': 'No se seleccionó ningún archivo.'})

        try:
            MovilXiaomi.objects.using('mongodb').all().delete()
            file_data = uploaded_file.read().decode("utf-8")
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)

            contador = 0

            current_id = 1

            for row in reader:
                movil = MovilXiaomi()

                movil.id = current_id

                # Adaptar claves según tu CSV
                movil.name = row.get('name', row.get('Name'))
                movil.imgURL = row.get('imgURL', row.get('Image'))

                try:
                    movil.price = int(float(row.get('price', row.get('Price', 0))))
                    movil.ratings = float(row.get('ratings', row.get('Ratings', 0.0)))
                    movil.ram = int(row.get('ram', row.get('RAM', 0)))
                    movil.storage = int(row.get('storage', row.get('Storage', 0)))
                    movil.camera = int(row.get('camera', 0))
                    movil.battery = int(row.get('battery', 0))
                except ValueError:
                    continue

                movil.save(using='mongodb')
                contador += 1
                current_id += 1

            mensaje = f"Se han cargado {contador} móviles correctamente."
            return render(request, 'data_load.html', {'mensaje': mensaje})

        except Exception as e:
            return render(request, 'data_load.html', {'error': f'Error al procesar el CSV: {e}'})

    return render(request, 'data_load.html')