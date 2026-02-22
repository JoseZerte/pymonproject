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
from .models import Usuario, MovilXiaomi, Valoracion, RankingPersonal, Categoria


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
    # RF6: Obtener todas las categorías para pintar los botones de filtro
    categorias = Categoria.objects.using('mongodb').all()

    # Comprobar si el usuario ha hecho clic en alguna categoría (?cat=1)
    cat_id = request.GET.get('cat')
    if cat_id:
        try:
            cat_seleccionada = Categoria.objects.using('mongodb').get(id=int(cat_id))
            # Traer solo los móviles que estén en la lista de esa categoría
            moviles = MovilXiaomi.objects.using('mongodb').filter(id__in=cat_seleccionada.moviles)
        except Categoria.DoesNotExist:
            moviles = MovilXiaomi.objects.using('mongodb').all()
    else:
        # Si no hay filtro, mostramos todos
        moviles = MovilXiaomi.objects.using('mongodb').all()

    mis_listas = RankingPersonal.objects.using('mongodb').filter(user_email=request.user.email)

    if request.method == 'POST' and 'btn_ranking_rapido' in request.POST:
        movil_id = int(request.POST.get('movil_id'))
        ranking_id = request.POST.get('ranking_seleccionado')
        if ranking_id:
            try:
                ranking = RankingPersonal.objects.using('mongodb').get(id=int(ranking_id))
                if isinstance(ranking.elementos, list):
                    ranking.elementos = {'S': [], 'A': [], 'B': [], 'C': [], 'D': [], 'unranked': ranking.elementos}
                ya_existe = any(movil_id in tier_list for tier_list in ranking.elementos.values())
                if not ya_existe:
                    ranking.elementos['unranked'].append(movil_id)
                    ranking.save(using='mongodb')
                    messages.success(request, f"¡Añadido a '{ranking.nombre}'!")
                else:
                    messages.info(request, f"El móvil ya estaba en la lista '{ranking.nombre}'")
            except Exception as e:
                messages.error(request, f"Error: {e}")
        # Mantenemos el filtro al recargar
        url_redirect = f"/catalogo/?cat={cat_id}" if cat_id else "/catalogo/"
        return redirect(url_redirect)

    return render(request, 'catalogo.html', {
        'moviles': moviles,
        'mis_listas': mis_listas,
        'categorias': categorias,  # Pasamos las categorías al HTML
        'cat_actual': int(cat_id) if cat_id else None
    })


@login_required(login_url='login')
def detalle_movil(request, movil_id):
    try:
        movil = MovilXiaomi.objects.using('mongodb').get(id=movil_id)
    except MovilXiaomi.DoesNotExist:
        messages.error(request, "El móvil no existe.")
        return redirect('catalogo')

    # 1. SOLUCIÓN AL CRASH: Buscamos la valoración más reciente (evita el error de si hay 2)
    mi_valoracion = Valoracion.objects.using('mongodb').filter(
        user_email=request.user.email,
        movil_id=movil_id
    ).order_by('-fecha').first()

    ya_votado = mi_valoracion is not None

    # 2. Lógica para guardar o editar la valoración
    if request.method == 'POST' and 'btn_votar' in request.POST:
        puntos = request.POST.get('rating')
        comentario = request.POST.get('comentario')

        if puntos:
            if not mi_valoracion:
                mi_valoracion = Valoracion()
                mi_valoracion.user_email = request.user.email
                mi_valoracion.movil_id = movil_id

            mi_valoracion.fecha = timezone.now()
            mi_valoracion.puntuacion = int(puntos)
            mi_valoracion.comentario = comentario
            mi_valoracion.save(using='mongodb')

            # Limpieza silenciosa: borramos duplicados viejos si los hubiera
            Valoracion.objects.using('mongodb').filter(
                user_email=request.user.email, movil_id=movil_id
            ).exclude(id=mi_valoracion.id).delete()

            mensaje = "¡Valoración actualizada!" if ya_votado else "¡Valoración guardada!"
            messages.success(request, mensaje)
            return redirect('detalle_movil', movil_id=movil_id)
        else:
            messages.error(request, "Selecciona al menos una estrella.")

    # 3. Lógica del Ranking
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
        'mi_valoracion': mi_valoracion,
        'valoraciones': valoraciones,
        'mis_listas': mis_listas
    })

#GESTIÓN DE RANKINGS

@login_required
def mis_rankings(request):


    #esta linea de aqui me sirve pa borrar por si acaso se queda la lista mal
    #RankingPersonal.objects.using('mongodb').filter(id=None).delete()

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

    # MIGRACIÓN AUTOMÁTICA: Convertir lista antigua a Tier List
    if isinstance(ranking.elementos, list):
        ranking.elementos = {
            'S': [], 'A': [], 'B': [], 'C': [], 'D': [],
            'unranked': ranking.elementos
        }
        ranking.save(using='mongodb')

    # Obtener todos los móviles que están en alguna caja
    all_ids = []
    for ids in ranking.elementos.values():
        all_ids.extend(ids)

    moviles_db = {m.id: m for m in MovilXiaomi.objects.using('mongodb').filter(id__in=all_ids)}

    # Construir las cajas con los objetos reales del móvil
    tiers_data = {
        'S': [moviles_db[i] for i in ranking.elementos.get('S', []) if i in moviles_db],
        'A': [moviles_db[i] for i in ranking.elementos.get('A', []) if i in moviles_db],
        'B': [moviles_db[i] for i in ranking.elementos.get('B', []) if i in moviles_db],
        'C': [moviles_db[i] for i in ranking.elementos.get('C', []) if i in moviles_db],
        'D': [moviles_db[i] for i in ranking.elementos.get('D', []) if i in moviles_db],
        'unranked': [moviles_db[i] for i in ranking.elementos.get('unranked', []) if i in moviles_db],
    }

    # Lógica para borrar un móvil de la Tier List
    if request.method == 'POST' and 'borrar_movil' in request.POST:
        try:
            movil_a_borrar = int(request.POST.get('movil_id_borrar'))
            for tier_name, tier_list in ranking.elementos.items():
                if movil_a_borrar in tier_list:
                    tier_list.remove(movil_a_borrar)
                    break
            ranking.save(using='mongodb')
            messages.success(request, "Móvil eliminado de la Tier List.")
            return redirect('ver_ranking', ranking_id=ranking_id)
        except ValueError:
            pass

    return render(request, 'ver_ranking.html', {
        'ranking': ranking,
        'tiers_data': tiers_data
    })


@csrf_exempt
@login_required
def guardar_orden_ranking(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ranking_id = data.get('ranking_id')
            nuevas_tiers = data.get('tiers')  # Ahora recibimos las cajas enteras

            ranking = RankingPersonal.objects.using('mongodb').get(id=ranking_id)

            if ranking.user_email == request.user.email:
                # Convertir todo a números enteros por si acaso
                for tier in nuevas_tiers:
                    nuevas_tiers[tier] = [int(x) for x in nuevas_tiers[tier]]

                ranking.elementos = nuevas_tiers
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

            # --- TASA DE CONVERSIÓN REAL (Rupias Indias a Euros) ---
            TASA_INR_EUR = 0.0111

            for row in reader:
                movil = MovilXiaomi()
                movil.id = current_id
                movil.name = row.get('name', row.get('Name'))
                movil.imgURL = row.get('imgURL', row.get('Image'))
                try:
                    # CONVERSIÓN DE MONEDA: Multiplicamos por la tasa oficial
                    precio_rupias = float(row.get('price', 0))
                    movil.price = round(precio_rupias * TASA_INR_EUR, 2)

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

            mensaje = f"Se han cargado {contador} móviles con conversión real de INR a Euros."
            return render(request, 'data_load.html', {'mensaje': mensaje})
        except Exception as e:
            return render(request, 'data_load.html', {'error': f'Error: {e}'})

    return render(request, 'data_load.html')


@login_required
def admin_catalogo(request):
    if request.user.rol != 'admin': return redirect('dashboard')
    moviles = MovilXiaomi.objects.using('mongodb').all()
    return render(request, 'admin_catalogo.html', {'moviles': moviles})


@login_required
def crear_movil(request):
    if request.user.rol != 'admin': return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Buscar el ID más alto de Mongo para sumar 1 (Auto-Incremental casero)
            ultimo_movil = MovilXiaomi.objects.using('mongodb').order_by('-id').first()
            nuevo_id = (ultimo_movil.id + 1) if ultimo_movil else 1

            nuevo = MovilXiaomi()
            nuevo.id = nuevo_id
            nuevo.name = request.POST.get('name')
            nuevo.price = float(request.POST.get('price', 0))
            nuevo.imgURL = request.POST.get('imgURL', 'https://via.placeholder.com/200')
            nuevo.ram = int(request.POST.get('ram', 0))
            nuevo.storage = int(request.POST.get('storage', 0))
            nuevo.battery = int(request.POST.get('battery', 0))
            nuevo.save(using='mongodb')

            messages.success(request, "¡Móvil creado con éxito!")
            return redirect('admin_catalogo')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'admin_form_movil.html', {'accion': 'Crear'})


@login_required
def editar_movil(request, movil_id):
    if request.user.rol != 'admin': return redirect('dashboard')

    try:
        movil = MovilXiaomi.objects.using('mongodb').get(id=movil_id)
    except MovilXiaomi.DoesNotExist:
        return redirect('admin_catalogo')

    if request.method == 'POST':
        try:
            movil.name = request.POST.get('name')
            movil.price = float(request.POST.get('price', 0))
            movil.imgURL = request.POST.get('imgURL', 'https://via.placeholder.com/200')
            movil.ram = int(request.POST.get('ram', 0))
            movil.storage = int(request.POST.get('storage', 0))
            movil.battery = int(request.POST.get('battery', 0))
            movil.save(using='mongodb')

            messages.success(request, "¡Móvil actualizado correctamente!")
            return redirect('admin_catalogo')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'admin_form_movil.html', {'accion': 'Editar', 'movil': movil})


@login_required
def borrar_movil(request, movil_id):
    if request.user.rol == 'admin':
        try:
            movil = MovilXiaomi.objects.using('mongodb').get(id=movil_id)
            movil.delete(using='mongodb')
            messages.success(request, "Móvil eliminado de la base de datos.")
        except:
            pass
    return redirect('admin_catalogo')


@login_required
def admin_categorias(request):
    if request.user.rol != 'admin': return redirect('dashboard')
    categorias = Categoria.objects.using('mongodb').all()
    return render(request, 'admin_categorias.html', {'categorias': categorias})


@login_required
def crear_categoria(request):
    if request.user.rol != 'admin': return redirect('dashboard')
    moviles_totales = MovilXiaomi.objects.using('mongodb').all()

    if request.method == 'POST':
        try:
            ultima = Categoria.objects.using('mongodb').order_by('-id').first()
            nuevo_id = (ultima.id + 1) if ultima else 1

            cat = Categoria()
            cat.id = nuevo_id
            cat.name = request.POST.get('name')
            cat.description = request.POST.get('description')

            # Recoger la lista de móviles seleccionados
            moviles_seleccionados = request.POST.getlist('moviles')
            cat.moviles = [int(m) for m in moviles_seleccionados]
            cat.save(using='mongodb')

            messages.success(request, "Categoría creada con éxito.")
            return redirect('admin_categorias')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'admin_form_categoria.html', {'accion': 'Crear', 'moviles_totales': moviles_totales})


@login_required
def editar_categoria(request, cat_id):
    if request.user.rol != 'admin': return redirect('dashboard')
    try:
        cat = Categoria.objects.using('mongodb').get(id=cat_id)
    except Categoria.DoesNotExist:
        return redirect('admin_categorias')

    moviles_totales = MovilXiaomi.objects.using('mongodb').all()

    if request.method == 'POST':
        try:
            cat.name = request.POST.get('name')
            cat.description = request.POST.get('description')
            moviles_seleccionados = request.POST.getlist('moviles')
            cat.moviles = [int(m) for m in moviles_seleccionados]
            cat.save(using='mongodb')

            messages.success(request, "Categoría actualizada correctamente.")
            return redirect('admin_categorias')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'admin_form_categoria.html',
                  {'accion': 'Editar', 'categoria': cat, 'moviles_totales': moviles_totales})


@login_required
def borrar_categoria(request, cat_id):
    if request.user.rol == 'admin':
        Categoria.objects.using('mongodb').filter(id=cat_id).delete()
        messages.success(request, "Categoría eliminada.")
    return redirect('admin_categorias')


@login_required
def estadisticas_globales(request):


    # 1. Total de valoraciones (RF9.33)
    total_valoraciones = Valoracion.objects.using('mongodb').count()

    # Traemos todo a memoria para calcular seguro sin que MongoDB de errores raros
    valoraciones = list(Valoracion.objects.using('mongodb').all())
    moviles = {m.id: m for m in MovilXiaomi.objects.using('mongodb').all()}
    categorias = list(Categoria.objects.using('mongodb').all())

    # Calculamos stats por móvil
    stats_m = {}
    for v in valoraciones:
        if v.movil_id not in stats_m:
            stats_m[v.movil_id] = {'votos': 0, 'suma': 0}
        stats_m[v.movil_id]['votos'] += 1
        stats_m[v.movil_id]['suma'] += v.puntuacion

    # 2. Top Móviles Más Valorados (RF9.31)
    top_moviles = []
    for mid, data in stats_m.items():
        if mid in moviles:
            top_moviles.append({
                'nombre': moviles[mid].name,
                'media': round(data['suma'] / data['votos'], 1),
                'votos': data['votos']
            })
    top_moviles.sort(key=lambda x: x['media'], reverse=True)
    top_moviles = top_moviles[:5]  # Solo los 5 mejores

    # 3. Promedio por Categoría (RF9.32)
    stats_cat = []
    for cat in categorias:
        c_votos, c_suma = 0, 0
        for mid in cat.moviles:
            if mid in stats_m:
                c_votos += stats_m[mid]['votos']
                c_suma += stats_m[mid]['suma']
        media = round(c_suma / c_votos, 1) if c_votos > 0 else 0
        stats_cat.append({'nombre': cat.name, 'media': media, 'votos': c_votos})

    # 4. Supervisión de Usuarios y Valoraciones Recientes (RF10.36)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    usuarios = User.objects.all()
    v_recientes = Valoracion.objects.using('mongodb').order_by('-fecha')[:5]

    # Adjuntamos el nombre del móvil a las valoraciones recientes para que se vea bonito
    for v in v_recientes:
        v.nombre_movil = moviles[v.movil_id].name if v.movil_id in moviles else "Móvil Borrado"

    return render(request, 'estadisticas.html', {
        'total': total_valoraciones,
        'top_moviles': top_moviles,
        'stats_cat': stats_cat,
        'usuarios': usuarios,
        'v_recientes': v_recientes
    })