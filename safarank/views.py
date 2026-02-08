import csv
import io
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegistroForm, LoginForm
from .models import Usuario, MovilXiaomi


# --- AUTENTICACIÓN (Tu código original) ---

def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registro.html', {'form': form})


def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, email=email, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('inicio')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_usuario(request):
    logout(request)
    return redirect('login')


# --- VISTAS PRINCIPALES ---

@login_required(login_url='login')
def inicio(request):
    # Traemos los móviles de MongoDB
    moviles = MovilXiaomi.objects.using('mongodb').all()

    return render(request, 'inicio.html', {
        'nombre_usuario': request.user.nombre,
        'rol_usuario': request.user.rol,
        'moviles': moviles
    })


# --- VISTAS DE ADMINISTRACIÓN (Lógica del Profesor adaptada) ---

@login_required(login_url='login')
def panel_administracion(request):
    # Verificamos si es admin (RF2)
    if request.user.rol != 'admin':
        return redirect('inicio')

    return render(request, 'admin.html')


@login_required(login_url='login')
def cargar_datos(request):
    # Seguridad: Solo admin puede cargar datos
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == "POST":
        # 'csvFile' debe ser el name del input en tu HTML
        uploaded_file = request.FILES.get('csvFile')

        if not uploaded_file:
            return render(request, 'data_load.html', {'error': 'No se seleccionó ningún archivo.'})

        try:
            # Decodificamos el archivo CSV
            file_data = uploaded_file.read().decode("utf-8")
            io_string = io.StringIO(file_data)
            # DictReader usa la primera fila del CSV como nombres de columnas
            reader = csv.DictReader(io_string)

            # Lista para guardar objetos antes de insertar (opcional, o uno a uno)
            contador = 0

            for row in reader:
                # Creamos el objeto MovilXiaomi
                movil = MovilXiaomi()

                # ASIGNACIÓN DE CAMPOS
                # IMPORTANTE: Las claves ['Name'], ['Price'] deben coincidir EXACTAMENTE
                # con la cabecera de tu archivo CSV.
                movil.name = row.get('name', row.get('Name'))
                movil.imgURL = row.get('imgURL', row.get('Image'))

                # Conversiones de tipos (El CSV devuelve texto, hay que pasar a int/float)
                try:
                    movil.price = int(float(row.get('price', row.get('Price', 0))))
                    movil.ratings = float(row.get('ratings', row.get('Ratings', 0.0)))
                    movil.ram = int(row.get('ram', row.get('RAM', 0)))
                    movil.storage = int(row.get('storage', row.get('Storage', 0)))
                    movil.camera = int(row.get('camera', 0))
                    movil.battery = int(row.get('battery', 0))
                except ValueError:
                    continue  # Si una fila falla en los números, la saltamos

                # Guardamos explícitamente en MongoDB
                movil.save(using='mongodb')
                contador += 1

            mensaje = f"Se han cargado {contador} móviles correctamente."
            return render(request, 'data_load.html', {'mensaje': mensaje})

        except Exception as e:
            return render(request, 'data_load.html', {'error': f'Error al procesar el CSV: {e}'})

    return render(request, 'data_load.html')