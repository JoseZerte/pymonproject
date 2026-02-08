from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

# Esta importación es necesaria para las listas de categorías en MongoDB (como lo tiene el profe)
try:
    from django_mongodb_backend.fields import ArrayField
except ImportError:
    # Si falla, usamos JSONField que funciona igual para listas
    from django.db.models import JSONField as ArrayField


# ---------------------------------------------------------
# 1. GESTIÓN DE USUARIOS (Mantenemos el tuyo antiguo)
# ---------------------------------------------------------

class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, rol, password=None):
        if not email:
            raise ValueError("El usuario debe tener un email")
        email = self.normalize_email(email)
        usuario = self.model(email=email, nombre=nombre, rol=rol)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, nombre, rol='admin', password=None):
        usuario = self.create_user(email, nombre, rol, password)
        usuario.is_superuser = True
        usuario.is_staff = True
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLES = (('admin', 'Administrador'), ('cliente', 'Cliente'))

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    # IMPORTANTE: Tú te logueas con EMAIL, no con nombre.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'rol']

    def __str__(self):
        return self.email


# ---------------------------------------------------------
# 2. MODELOS DE MONGODB (Xiaomi + Requisitos del Profe)
# ---------------------------------------------------------

class MovilXiaomi(models.Model):
    # Usamos tus campos, pero añadimos default=0 para que no falle al cargar CSVs incompletos
    name = models.CharField(max_length=255)
    ratings = models.FloatField(default=0.0)
    price = models.IntegerField(default=0)
    imgURL = models.URLField(max_length=900)
    camera = models.IntegerField(default=0)
    display = models.CharField(max_length=100, default="N/A")
    battery = models.IntegerField(default=0)
    storage = models.IntegerField(default=0)
    ram = models.IntegerField(default=0)
    processor = models.CharField(max_length=150, default="N/A")
    android_version = models.IntegerField(default=12)

    class Meta:
        managed = False
        db_table = 'safarank'  # Tu colección de móviles

    def __str__(self):
        return self.name


# --- Nuevas tablas obligatorias para el proyecto ---

class Categoria(models.Model):
    code = models.IntegerField(null=False, unique=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=300)
    # Aquí guardaremos los IDs de los móviles que pertenecen a esta categoría
    # Ejemplo: [101, 102, 305]
    moviles = ArrayField(models.IntegerField(), null=True, blank=True, default=list)

    class Meta:
        managed = False
        db_table = 'categorias'

    def __str__(self):
        return self.name


class Valoracion(models.Model):  # Review
    user_email = models.CharField(max_length=150)  # Guardamos el email del usuario que vota
    movil_name = models.CharField(max_length=255)  # Guardamos el nombre del móvil votado
    fecha = models.DateField(default=timezone.now)
    puntuacion = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField()

    class Meta:
        managed = False
        db_table = 'valoraciones'