from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Usuario


class RegistroForm(forms.ModelForm):
    # Definimos la contraseña con un widget de tipo Password para que no se vea al escribir
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        # Estos son los campos que el usuario rellenará
        fields = ['email', 'nombre', 'rol', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),  # Esto crea el desplegable
        }


class LoginForm(AuthenticationForm):
    # Sobrescribimos el campo username para que pida el Correo
    username = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'form-control'}))