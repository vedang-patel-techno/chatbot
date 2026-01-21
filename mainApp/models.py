from django.db import models

class Logininfo(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

class Bloginfo(models.Model):
    blog = models.CharField(max_length=255)
    user = models.IntegerField()


