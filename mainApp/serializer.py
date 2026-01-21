from rest_framework import serializers
from .models import Logininfo,Bloginfo

class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logininfo              # tell DRF which model to serialize
        fields = '__all__'  

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model= Bloginfo
        fields="__all__"