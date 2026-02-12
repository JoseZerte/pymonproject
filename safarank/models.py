from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Importamos JSONField para manejar listas en MongoDB (funciona mejor que ArrayField a veces)
from django.db.models import JSONField


# ---------------------------------------------------------
# 1. GESTIÓN DE USUARIOS (SQLite - Auth)
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'rol']

    def __str__(self):
        return self.email


# ---------------------------------------------------------
# 2. MODELOS DE MONGODB (Datos del negocio)
# ---------------------------------------------------------

class MovilXiaomi(models.Model):
    id = models.IntegerField(primary_key=True)

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
        db_table = 'xiaomirank'

    def __str__(self):
        return self.name


class Categoria(models.Model):
    code = models.IntegerField(unique=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=300)
    moviles = JSONField(default=list, blank=True)

    class Meta:
        managed = False
        db_table = 'categorias'

    def __str__(self):
        return self.name


class Valoracion(models.Model):
    # Relación lógica: Guardamos el email del usuario (SQLite) aquí en Mongo
    user_email = models.CharField(max_length=150)

    # Guardamos el ID del móvil de Mongo
    movil_id = models.IntegerField()

    fecha = models.DateTimeField(default=timezone.now)
    puntuacion = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.TextField(max_length=500)

    class Meta:
        managed = False
        db_table = 'valoraciones'

    def __str__(self):
        return f"{self.user_email} - {self.movil_id}: {self.puntuacion}"


class RankingPersonal(models.Model):
    user_email = models.CharField(max_length=150)
    nombre = models.CharField(max_length=150)
    # Lista de IDs de móviles
    elementos = JSONField(default=list)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'rankings'

    def __str__(self):
        return f"{self.nombre} ({self.user_email})"