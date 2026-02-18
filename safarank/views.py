import csv
import io
import json
import random
from collections import defaultdict  # <--- IMPORTANTE PARA ESTADÍSTICAS

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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
                return redirect('dashboard')
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
def dashboard(request):
    return render(request, 'dashboard.html', {
        'nombre_usuario': request.user.nombre,
        'rol_usuario': request.user.rol
    })


@login_required(login_url='login')
def catalogo(request):
    moviles = MovilXiaomi.objects.using('mongodb').all()
    return render(request, 'catalogo.html', {
        'moviles': moviles
    })


@login_required(login_url='login')
def detalle_movil(request, movil_id):
    try:
        movil = MovilXiaomi.objects.using('mongodb').get(id=movil_id)
    except MovilXiaomi.DoesNotExist:
        messages.error(request, "El móvil no existe.")
        return redirect('catalogo')

    ya_votado = Valoracion.objects.using('mongodb').filter(
        user_email=request.user.email,
        movil_id=movil_id
    ).exists()

    if request.method == 'POST' and 'btn_votar' in request.POST:
        if ya_votado:
            messages.warning(request, "Ya has valorado este móvil.")
        else:
            puntos = request.POST.get('rating')
            comentario = request.POST.get('comentario')

            if puntos:
                valoracion = Valoracion()
                valoracion.user_email = request.user.email
                valoracion.movil_id = movil_id
                valoracion.fecha = timezone.now()
                valoracion.puntuacion = int(puntos)
                valoracion.comentario = comentario
                valoracion.save(using='mongodb')
                messages.success(request, "¡Valoración guardada!")
                return redirect('detalle_movil', movil_id=movil_id)
            else:
                messages.error(request, "Selecciona una estrella.")

    mis_listas = RankingPersonal.objects.using('mongodb').filter(user_email=request.user.email)

    if request.method == 'POST' and 'btn_ranking' in request.POST:
        ranking_id = request.POST.get('ranking_seleccionado')
        if ranking_id:
            try:
                ranking = RankingPersonal.objects.using('mongodb').get(id=int(ranking_id))
                if movil_id not in ranking.elementos:
                    ranking.elementos.append(movil_id)
                    ranking.save(using='mongodb')
                    messages.success(request, f"Añadido a '{ranking.nombre}'")
                else:
                    messages.info(request, f"Ya estaba en '{ranking.nombre}'")
            except Exception as e:
                messages.error(request, f"Error: {e}")
            return redirect('detalle_movil', movil_id=movil_id)

    valoraciones = Valoracion.objects.using('mongodb').filter(movil_id=movil_id).order_by('-fecha')

    return render(request, 'detalle_movil.html', {
        'movil': movil,
        'ya_votado': ya_votado,
        'valoraciones': valoraciones,
        'mis_listas': mis_listas
    })


# --- GESTIÓN DE RANKINGS ---

@login_required
def mis_rankings(request):
    rankings = RankingPersonal.objects.using('mongodb').filter(user_email=request.user.email)

    if request.method == 'POST':
        form = RankingForm(request.POST)
        if form.is_valid():
            nuevo = form.save(commit=False)
            nuevo.id = random.randint(10000, 999999)
            nuevo.user_email = request.user.email
            nuevo.save(using='mongodb')
            messages.success(request, "Ranking creado.")
            return redirect('mis_rankings')
    else:
        form = RankingForm()

    return render(request, 'mis_rankings.html', {'rankings': rankings, 'form': form})


@login_required
def ver_ranking(request, ranking_id):
    try:
        ranking = RankingPersonal.objects.using('mongodb').get(id=ranking_id)
    except RankingPersonal.DoesNotExist:
        return redirect('mis_rankings')

    if ranking.user_email != request.user.email:
        return redirect('dashboard')

    moviles_db = list(MovilXiaomi.objects.using('mongodb').filter(id__in=ranking.elementos))

    moviles_ordenados = []
    for id_movil in ranking.elementos:
        for movil in moviles_db:
            if movil.id == id_movil:
                moviles_ordenados.append(movil)
                break

    if request.method == 'POST' and 'borrar_movil' in request.POST:
        try:
            movil_a_borrar = int(request.POST.get('movil_id_borrar'))
            if movil_a_borrar in ranking.elementos:
                ranking.elementos.remove(movil_a_borrar)
                ranking.save(using='mongodb')
                messages.success(request, "Eliminado.")
                return redirect('ver_ranking', ranking_id=ranking_id)
        except ValueError:
            pass

    return render(request, 'ver_ranking.html', {
        'ranking': ranking,
        'moviles': moviles_ordenados
    })


@csrf_exempt
@login_required
def guardar_orden_ranking(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ranking_id = data.get('ranking_id')
            nuevo_orden = data.get('orden')

            ranking = RankingPersonal.objects.using('mongodb').get(id=ranking_id)

            if ranking.user_email == request.user.email:
                ranking.elementos = [int(x) for x in nuevo_orden]
                ranking.save(using='mongodb')
                return JsonResponse({'status': 'ok'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No autorizado'}, status=403)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def borrar_ranking(request, ranking_id):
    if ranking_id == 0: return redirect('mis_rankings')
    try:
        ranking = RankingPersonal.objects.using('mongodb').get(id=ranking_id)
        if ranking.user_email == request.user.email:
            ranking.delete(using='mongodb')
            messages.success(request, "Ranking eliminado.")
    except RankingPersonal.DoesNotExist:
        pass
    return redirect('mis_rankings')


# --- ESTADÍSTICAS (ESTO ES LO QUE TE FALTABA) ---

@login_required
def estadisticas(request):
    todas_valoraciones = Valoracion.objects.using('mongodb').all()
    total_votos = len(todas_valoraciones)
    promedio_global = 0
    top_moviles = []

    if total_votos > 0:
        suma_total = sum(v.puntuacion for v in todas_valoraciones)
        promedio_global = round(suma_total / total_votos, 2)

        notas_por_movil = defaultdict(list)
        for v in todas_valoraciones:
            notas_por_movil[v.movil_id].append(v.puntuacion)

        ranking_calc = []
        for mid, notas in notas_por_movil.items():
            media = sum(notas) / len(notas)
            ranking_calc.append((mid, media, len(notas)))

        ranking_calc.sort(key=lambda x: x[1], reverse=True)
        top_5_data = ranking_calc[:5]

        for item in top_5_data:
            mid, media, count = item
            try:
                movil = MovilXiaomi.objects.using('mongodb').get(id=mid)
                top_moviles.append({
                    'obj': movil,
                    'media': round(media, 1),
                    'total': count
                })
            except MovilXiaomi.DoesNotExist:
                continue

    return render(request, 'estadisticas.html', {
        'total_votos': total_votos,
        'promedio_global': promedio_global,
        'top_moviles': top_moviles
    })


# --- ADMIN ---

@login_required
def panel_administracion(request):
    if request.user.rol != 'admin':
        return redirect('dashboard')
    return render(request, 'admin.html')


@login_required
def cargar_datos(request):
    if request.user.rol != 'admin':
        return redirect('dashboard')

    if request.method == "POST":
        uploaded_file = request.FILES.get('csvFile')
        if not uploaded_file:
            return render(request, 'data_load.html', {'error': 'Falta archivo.'})
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
                movil.name = row.get('name', row.get('Name'))
                movil.imgURL = row.get('imgURL', row.get('Image'))
                try:
                    movil.price = int(float(row.get('price', 0)))
                    movil.ratings = float(row.get('ratings', 0.0))
                    movil.ram = int(row.get('ram', 0))
                    movil.storage = int(row.get('storage', 0))
                    movil.camera = int(row.get('camera', 0))
                    movil.battery = int(row.get('battery', 0))
                except ValueError:
                    continue
                movil.save(using='mongodb')
                contador += 1
                current_id += 1
            mensaje = f"Se han cargado {contador} móviles."
            return render(request, 'data_load.html', {'mensaje': mensaje})
        except Exception as e:
            return render(request, 'data_load.html', {'error': f'Error: {e}'})
    return render(request, 'data_load.html')