from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm, DeveloperRegistrationForm
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login
from .utils import send_email_otp, send_welcome_email
from django.views.decorators.csrf import csrf_exempt
from .models import User,Developer
from django.http import JsonResponse,HttpResponse
import json
from django.contrib.auth import get_user_model
from .utils import send_email_otp
from django.http import JsonResponse
from .serializer import UserRegistrationSerializer, DeveloperRegistrationSerializer,DeveloperSerializer
import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .utils import send_developer_status_email
import requests

# Set up logging
logger = logging.getLogger(__name__)

# API for User Registration
class UserRegistration(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# API for Developer Registration
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import Developer
from .serializer import DeveloperRegistrationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

class DeveloperRegistration(APIView):
    def post(self, request, *args, **kwargs):
        # The email is the key to finding the user from the OTP step.
        email = request.data.get('email')
        password = request.data.get('password')
        # Get the new username from the request data
        username = request.data.get('username')

        # --- VALIDATION ---
        if not all([email, password, username]):
            return Response({'detail': 'Email, username, and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.data.get('organization_name'):
             return Response({'detail': 'Organization name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the desired username is already taken by a *different* user.
        if User.objects.filter(username=username).exclude(email=email).exists():
            return Response({'detail': 'This username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # --- LOGIC ---
        try:
            # Step 1: Find the user that was created during the OTP step.
            user = User.objects.get(email=email)
            
            if Developer.objects.filter(user=user).exists():
                return Response({'detail': 'This user is already registered as a developer.'}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'detail': 'User not found. Please complete the initial registration step first.'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Update the existing user with the final username and password.
        user.username = username  # <-- SET THE FINAL USERNAME
        user.set_password(password)
        user.is_developer = True
        user.save()

        # Step 3: Create the associated Developer profile with the remaining data.
        developer_data = {
            'user': user,
            'organization_name': request.data.get('organization_name'),
            'organization_address': request.data.get('organization_address'),
            'organization_website': request.data.get('organization_website', ''),
            'city': request.data.get('city'),
            'woreda': request.data.get('woreda'),
            'zone': request.data.get('zone', ''),
            'sub_city': request.data.get('sub_city', ''),
            'business_registration_number': request.data.get('business_registration_number'),
            'status': 'pending'
        }

        developer = Developer.objects.create(**developer_data)
        send_developer_status_email(developer)

        serializer = DeveloperRegistrationSerializer(developer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class UserRegistration(APIView):
    def post(self, request, *args, **kwargs):
        # Extract fields
        google_id_token = request.data.get('google_id_token')
        email = request.data.get('email')
        password = request.data.get('password')
        username = request.data.get('username')
        first_name = request.data.get('firstName')
        last_name=request.data.get('lastName')
        mobile_number = request.data.get('mobile_number')
        date_of_birth = request.data.get('date_of_birth')
        gender = request.data.get('gender')
        captcha = request.data.get('captcha')
        is_developer = request.data.get('is_developer', False)
        if google_id_token:
            # Verify the Google ID token
            try:
                id_info = id_token.verify_oauth2_token(
                    google_id_token, requests.Request(), '<YOUR_GOOGLE_CLIENT_ID>'
                )
                email = id_info.get('email')
                first_name = id_info.get('given_name')
                last_name = id_info.get('family_name')

                # Ensure email is verified
                if not id_info.get('email_verified'):
                    return Response({'detail': 'Email not verified by Google.'}, status=status.HTTP_400_BAD_REQUEST)

                # Check if email already exists
                existing_user = User.objects.filter(email=email).first()
                if existing_user:
                    return Response({'detail': 'Email is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

                # Generate a random username if not provided
                if not username:
                    username = email.split('@')[0]

                # Create user without a password for Google registration
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    mobile_number=mobile_number,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    is_developer=is_developer,
                )
                user.set_unusable_password()  # Mark as passwordless
                user.save()

                # Serialize and return response
                serializer = UserRegistrationSerializer(user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except ValueError:
                return Response({'detail': 'Invalid Google ID token.'}, status=status.HTTP_400_BAD_REQUEST)
        # Field validation: Check each field individually
        # if not full_name:
        #     return Response({'detail': 'Full name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({'detail': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'detail': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not username:
            return Response({'detail': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not mobile_number:
            return Response({'detail': 'Mobile number is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not date_of_birth:
            return Response({'detail': 'Date of birth is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not gender:
            return Response({'detail': 'Gender is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not first_name:
            return Response({'detail': 'firstname is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not last_name:
            return Response({'detail': 'lastname is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # if not captcha:
        #     return Response({'detail': 'Captcha verification is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 6:
            return Response({'detail': 'Password must be at least 6 characters long.'}, status=status.HTTP_400_BAD_REQUEST)
        if password.isdigit() or password.isalpha():
            return Response({'detail': 'Password must contain both letters and numbers.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email is already registered
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if not is_developer and not existing_user.is_developer:
                return Response({'detail': 'Email is already registered as a regular user.'}, status=status.HTTP_400_BAD_REQUEST)
            elif is_developer and existing_user.is_developer:
                return Response({'detail': 'Email is already registered as a developer.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
        # Create user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            date_of_birth=date_of_birth,
            gender=gender,
            is_developer=False  # Non-developer registration
        )
        user.set_password(password)  # Set the password securely
        user.save()

        # Send welcome email
        send_welcome_email(user)

        # Serialize and return response
        serializer = UserRegistrationSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt
def send_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON body received in send_otp request.")
            return JsonResponse({"error": "Invalid JSON format."}, status=400)

        email = data.get("email")

        # Validation: Only the email is needed now.
        if not email:
            return JsonResponse({"error": "Email is required."}, status=400)

        otp = generate_otp()
        logger.info(f"Generated OTP: {otp} for email: {email}")
        
        # This call is now correct because send_email_otp expects an email
        success = send_email_otp(email, otp) 

        if success:
            user, created = User.objects.get_or_create(email=email, defaults={"username": email})
            user.email_otp = otp
            user.otp_created_at = timezone.now()
            user.save()
            
            logger.info(f"Saved OTP: {otp} for user identified by email: {email}")
            # Change the message back to email
            return JsonResponse({"message": "OTP sent to your email."}, status=200)
        
        return JsonResponse({"error": "Failed to send OTP."}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

def generate_otp():
    import random
    import string
    otp = ''.join(random.choices(string.digits, k=6))
    return otp

def send_email_otp(email, otp):
    """
    Sends an OTP to the user's email address.
    """
    subject = 'Your OTP Code'
    message = f'Your OTP code is {otp}.'
    recipient_list = [email]
    
    try:
        # This uses the EMAIL_* settings from your settings.py file
        send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list, fail_silently=False)
        logger.info(f"Successfully sent email OTP to {email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt
def verify_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON body.")
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        email = data.get("email")
        otp = data.get("otp")

        if not email or not otp:
            return JsonResponse({"error": "Email and OTP are required."}, status=400)

        logger.info(f"Verifying OTP: {otp} for email: {email}")

        otp_expiry_time = timezone.now() - timedelta(minutes=10)  # OTP valid for 10 minutes

        try:
            user = User.objects.get(email=email, email_otp=otp, otp_created_at__gte=otp_expiry_time)
            logger.info(f"User found: {user.username} for OTP verification")

            user.is_email_verified = False
            user.email_otp = None
            user.otp_created_at = None
            user.save()
            return JsonResponse({"message": "Email verified successfully!"}, status=200)
        except User.DoesNotExist:
            logger.error("User not found or invalid OTP")
            return JsonResponse({"error": "Invalid OTP or email."}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=405)





from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from .models import Developer

User = get_user_model()

class CustomLoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Authenticate the user
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'detail': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if the user is a developer
        # if not user.is_developer:
        #     return Response({'detail': 'Access restricted. User is not a developer.'}, status=status.HTTP_403_FORBIDDEN)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        response_data = {
            'access_token': str(access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_developer': user.is_developer,
            }
        }

        # Include developer status if the user is a developer
        if user.is_developer and hasattr(user, 'developer'):
            developer = Developer.objects.get(user=user)
            response_data['user']['status'] = user.developer.status
            response_data['developer_info'] = DeveloperSerializer(developer).data  # Include detailed developer info

        return Response(response_data, status=status.HTTP_200_OK)
    

# Home page view
def home(request):
    return HttpResponse('')
  # Render home template

class ForgotPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        is_developer = request.data.get('is_developer')
        
        if not email or is_developer is None :
            return Response({'detail': 'Email and is_developer are required.'}, status=status.HTTP_400_BAD_REQUEST) 

        try:
            user = User.objects.get(email=email, is_developer=is_developer)
            otp = generate_otp()
            user.email_otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            # Send OTP via email
            send_mail(
                subject="Password Reset OTP",
                message=f"Your password reset OTP is: {otp}. This OTP will expire in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            return Response({'message': 'Password reset OTP sent to your email.'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'detail': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyResetOTPView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        otp = request.data.get('otp')
        is_developer = request.data.get('is_developer')
        
        
        if not email or not otp:
            return Response({'detail': 'Email and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email, is_developer=is_developer)
            
            
            # Check if OTP matches and is not expired (3 minutes validity)
            if user.email_otp != otp:
                return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user.otp_created_at or (timezone.now() - user.otp_created_at).total_seconds() > 180:  # 3 minutes
                return Response({'detail': 'OTP has expired.'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a temporary token for password reset
            token = RefreshToken.for_user(user)
            return Response({
                'message': 'OTP verified successfully.',
                'token': str(token.access_token)
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'detail': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        is_developer = request.data.get('is_developer')
        
        if not email or not new_password:
            return Response({'detail': 'Email and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email, is_developer=is_developer)
            
            # Validate password
            if len(new_password) < 6:
                return Response({'detail': 'Password must be at least 6 characters long.'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            if new_password.isdigit() or new_password.isalpha():
                return Response({'detail': 'Password must contain both letters and numbers.'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(new_password)
            user.email_otp = None  # Clear the OTP
            user.otp_created_at = None  # Clear the OTP timestamp
            user.save()

            return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'detail': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChangeDeveloperPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not all([current_password, new_password]):
            return Response({
                'detail': 'Current password and new password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user from the request (authenticated via token)
            user = request.user
            
            # Verify if user is a developer
            if not user.is_developer:
                return Response({
                    'detail': 'This account is not registered as a developer.'
                }, status=status.HTTP_403_FORBIDDEN)

            # Verify current password
            if not user.check_password(current_password):
                return Response({
                    'detail': 'Current password is incorrect.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate new password
            if len(new_password) < 6:
                return Response({
                    'detail': 'New password must be at least 6 characters long.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if new_password.isdigit() or new_password.isalpha():
                return Response({
                    'detail': 'New password must contain both letters and numbers.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if new password is same as current password
            if current_password == new_password:
                return Response({
                    'detail': 'New password cannot be the same as current password.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(new_password)
            user.save()

            return Response({
                'message': 'Developer password changed successfully.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
