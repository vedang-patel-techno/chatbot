from django.contrib import admin
from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter
from .views import apiEnd,myprofileapi , login , register

urlpatterns=[
    path('',views.firstpage,name="homepage"),
    path('login/', login,name="login"),
    path('register/',register,name='register'),
    path('allBlogs/',views.allBlogs,name="allblogs"),
    path('api/',apiEnd.as_view(),name="api"),
    path('addblog/',views.addblog,name="addblog"),
    path('profile/',views.profile,name="profile"),
    path('myprofileapi/',myprofileapi.as_view(),name="userblog")
]