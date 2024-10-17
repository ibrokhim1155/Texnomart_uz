from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from texnomart.serializers import UserRegisterSerializer, UserLoginSerializer


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            refresh_token = RefreshToken(refresh_token)
            refresh_token.blacklist()
            return Response({
                'Details': 'Successfully logged out.',
                'refresh_token': str(refresh_token)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'Details': 'Something went wrong.',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(CreateAPIView):
    serializer_class = UserRegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        self.response_data = {
            "message": "User created successfully",
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data.update(self.response_data)
        return response


class LoginView(GenericAPIView):
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            password = serializer.validated_data.get('password')

            user = authenticate(username=username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "username": user.username,
                    "email": user.email
                }, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
