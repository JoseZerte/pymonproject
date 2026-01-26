from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import RegistroForm, LoginForm
from .models import Usuario

def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False) #
            usuario.set_password(form.cleaned_data['password']) #
            usuario.save() #
            return redirect('login')
    else:
        form = RegistroForm()
    # Ahora busca directamente 'registro.html' en tu carpeta templates
    return render(request, 'registro.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, email=email, password=password) #
            if usuario is not None:
                login(request, usuario) #
                return redirect('inicio')
    else:
        form = LoginForm()
    # Ahora busca directamente 'login.html'
    return render(request, 'login.html', {'form': form})

def logout_usuario(request):
    logout(request) #
    return redirect('login')

def inicio(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # Ahora busca directamente 'inicio.html'
    return render(request, 'inicio.html', {
        'nombre_usuario': request.user.nombre,
        'rol_usuario': request.user.rol
    })