from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Usuario, Valoracion, RankingPersonal

# --- FORMULARIOS DE USUARIO (SQLite) ---

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'rol', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data


class LoginForm(forms.Form):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))


# --- FORMULARIOS DE MONGODB (Valoraciones y Rankings) ---

class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['puntuacion', 'comentario']
        labels = {
            'puntuacion': 'Puntuación (1-5)',
            'comentario': 'Tu opinión'
        }
        widgets = {
            'puntuacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class RankingForm(forms.ModelForm):
    class Meta:
        model = RankingPersonal
        fields = ['nombre']
        labels = {
            'nombre': 'Nombre de tu lista (Ranking)'
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mis Xiaomis favoritos para jugar'}),
        }