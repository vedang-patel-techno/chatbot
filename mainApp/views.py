from django.shortcuts import render, redirect
from .models import Logininfo
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Bloginfo,Logininfo
from .serializer import userSerializer,BlogSerializer
from rest_framework.response import Response
import requests
from django.contrib.auth.decorators import login_required
from rest_framework import status


def firstpage(request):
    return render(request, 'loginRegister.html')

def register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
  
        if not Logininfo.objects.filter(email=email).exists():
            user = Logininfo(name=name, email=email, password=password)  
            user.save()
            request.session['user_id'] = user.id
            return redirect('/allBlogs/')  
        else:
            return render(request, 'loginRegister.html', {'error': 'User already exists'})

    return render(request, 'loginRegister.html')


def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = Logininfo.objects.filter(email=email, password=password).first()
        if user:
            request.session['user_id'] = user.id
            return redirect('/allBlogs/')  
        else:
            return render(request, 'loginRegister.html', {'error': 'Invalid credentials'})
    return render(request, 'loginRegister.html')


class apiEnd(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        blogs = Bloginfo.objects.all()
        serializer = BlogSerializer(blogs, many=True)
        return Response(serializer.data)

class myprofileapi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user_id = request.session.get('user_id')
        if user_id:
            blogs = Bloginfo.objects.filter(user=user_id)  # only user's blogs
        else:
            blogs = Bloginfo.objects.none()  # empty if not logged in
        serializer = BlogSerializer(blogs, many=True)
        return Response(serializer.data, status=200)
    
@login_required
def allBlogs(request):
        blogs = Bloginfo.objects.all()
        data = BlogSerializer(blogs, many=True).data
        return render(request, 'allBlogs.html', {'data': data})

@login_required
def addblog(request):
    if request.method == 'POST':
        if request.method == 'POST':
            blog_text = request.POST.get('blog')
            user_id = request.session.get('user_id')

            if user_id: # type: ignore
                Bloginfo.objects.create(blog=blog_text, user=user_id) # type: ignore
                url = "http://127.0.0.1:8000/api/"
                data=requests.get(url)
                return redirect('/allBlogs/')
            else:
                return redirect('/login/')  


def profile(request):
    url = "http://127.0.0.1:8000/myprofileapi/"
# Get the sessionid cookie from the current request
    cookies = {'sessionid': request.COOKIES.get('sessionid')}
    response = requests.get(url, cookies=cookies)
    if response.status_code == 200:
        data = response.json()
    else:
        data = []
    return render(request, 'myprofile.html', {"data": data})