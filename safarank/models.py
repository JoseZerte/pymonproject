import datetime

from django.core.validators import MaxValueValidator
from django.db import models
from django.conf import settings
from django_mongodb_backend.fields import EmbeddedModelField, ArrayField
from django_mongodb_backend.models import EmbeddedModel

class Character(EmbeddedModel):
    code= models.IntegerField(null=False)
    firstName= models.CharField(max_length=150)
    lastName = models.CharField(max_length=150)
    fullname= models.CharField(max_length=300)
    title= models.CharField(max_length=300)
    family= models.CharField(max_length=100)
    image= models.CharField(max_length=300)
    imageUrl= models.CharField(max_length=800)
    categories = ArrayField(models.IntegerField(), null= True, blank=True,  default=list)


    # esto define el nombre de la tabla, por si esta diferente
    class Meta:
        db_table = 'characters'
        managed = False

        def __str__(self):
            return self.fullName

        class Category(EmbeddedModel):
            name= models.CharField(max_length=100, unique=True)
            description= models.CharField(max_length=300)

            class Meta:
                db_table = 'categories'

            def __str__(self):
                return self.name


    class Review(EmbeddedModel):
       user = models.CharField(max_length=100)
       character = models.IntegerField(null=False)
       reviewDate = models.DateField(default=datetime.now())
       rating = models.PositiveIntegerField(null=False, validators=[MaxValueValidator(5), MinValueValidator(1)])
       comments = models.TextField()


       def __str__(self):
           return self.user + "" + str(self.rating)


       class Meta:
           db_table = 'reviews'
           managed = False


           class Ranking(EmbeddedModel):
               user =models.CharField(max_length=100)
               rankingDate = models.DateField(default=datetime.datetime.now())
               categoryCode = models.IntegerField(null=False)
               rankingList = ArrayField(models.IntegerField(), null= True, blank=True,  default=list)