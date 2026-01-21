from rest_framework import serializers
from .models import Logininfo, Bloginfo

class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logininfo  # the model you want to serialize
        fields = '__all__'  # include all fields (or list them: ['name', 'email', 'password', 'userId'])

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bloginfo
        fields = ['blog','user']  # or ['blog', 'blogId', 'userId']
