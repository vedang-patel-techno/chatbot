# Register your models here.
from django.contrib import admin
from .models import Logininfo, Bloginfo

# Register your models here
@admin.register(Logininfo)
class LogininfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'email','password')
    search_fields = ('name', 'email')

@admin.register(Bloginfo)
class BloginfoAdmin(admin.ModelAdmin):
    list_display = ('blog','user')
     # search_fields = ('blog')
