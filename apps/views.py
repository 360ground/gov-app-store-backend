import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import AppSubmissionForm
from .models import App  # Make sure the App model is imported
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import AppSubmissionSerializer
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import App,Screenshot
from .serializers import AppSerializer
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework.generics import RetrieveAPIView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .serializers import ReviewSerializer
from .models import Review
from django.db.models import Q
from django.db import transaction
from django.core.files.base import ContentFile

class SubmitNewAppView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # To handle file uploads
    
    def post(self, request, *args, **kwargs):
        # Ensure the user is a developer
        if not request.user.is_developer:
            return Response({'detail': 'Access restricted. User is not a developer.'}, status=status.HTTP_403_FORBIDDEN)

        # Get screenshots and read their content immediately to prevent deletion
        screenshots = request.FILES.getlist('screenshots_upload')
        screenshot_data = []
        
        # Read file content immediately to prevent temp file deletion
        for screenshot in screenshots:
            screenshot_data.append({
                'name': screenshot.name,
                'content': screenshot.read(),
                'content_type': screenshot.content_type
            })
            # Reset file pointer for potential reuse
            screenshot.seek(0)
        
        # Don't copy request.data when it contains files - just use it directly
        serializer = AppSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            # Use database transaction to ensure all operations succeed or fail together
            try:
                with transaction.atomic():
                    # Save the app instance
                    app = serializer.save(developer=request.user, status='Pending')

                    # Handle uploaded screenshots using the stored content
                    for data in screenshot_data:
                        # Create a new file object from the stored content
                        file_obj = ContentFile(data['content'], name=data['name'])
                        Screenshot.objects.create(app=app, screenshot=file_obj)

                # Include screenshots in the response (outside transaction)
                response_data = AppSubmissionSerializer(app).data
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'detail': f'Error saving app data: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeveloperAppsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        developer_apps = App.objects.filter(developer=request.user)
        pending_count = developer_apps.filter(status='Pending').count()
        approved_count = developer_apps.filter(status='Approved').count()
        rejected_count = developer_apps.filter(status='Rejected').count()
        app_list = [
            {
                'id':app.id,
                'app_name': app.app_name,
                'category': app.category,
                'status': app.status,
                'created_at': app.created_at,
                'app_version': app.app_version,
                'tags': app.tags,
                'status':app.status
            }
            for app in developer_apps
        ]
        total_apps = developer_apps.count()

        return Response({
            'developer': request.user.username,
            'id':request.user.id,
            'total_apps': total_apps,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'apps': app_list,
        })



class AppListView(APIView):
    def get(self, request):
        apps = App.objects.filter(status='Approved')
        serializer = AppSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AppListViewAll(APIView):
    def get(self, request):
        apps = App.objects.all() 
        serializer = AppSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)  

def app_listing(request):
    apps = App.objects.filter(status='Approved') 
    return render(request, 'apps/app_listing.html', {'apps': apps})

def submitted_apps(request):
    apps = App.objects.filter(developer=request.user)
    return render(request, 'apps/submitted_apps.html', {'apps': apps})



class AppDetailView(generics.RetrieveAPIView):
    queryset = App.objects.filter(status='Approved')
    serializer_class = AppSerializer
    lookup_field = 'id'


class AppDetailViewAll(RetrieveAPIView):
    serializer_class = AppSerializer
    lookup_field = 'id'  # Field used to identify the object (e.g., primary key)

    def get_queryset(self):
        """
        Returns all apps so any app, regardless of its status, can be retrieved.
        """
        return App.objects.all()  # Query all apps


logger = logging.getLogger(__name__)
@csrf_exempt
def increment_view_count(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON request
            app_id = data.get('appId')
            logger.info("Received data: %s", data)     
            
            if not app_id:
                return JsonResponse({'error': 'App ID is required'}, status=400)

            app = get_object_or_404(App, id=app_id)
            app.view_count += 1
            app.save()

            return JsonResponse({'message': 'View count updated successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
class AppReviewView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, app_id):
        app = get_object_or_404(App, id=app_id, status='Approved')
        reviews = app.reviews.all()  # Fetch related reviews
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, app_id):
        app = get_object_or_404(App, id=app_id, status='Approved')
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, app=app)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppSearchView(APIView):
    def get(self, request):
        # Retrieve query parameters
        query = request.GET.get('query', '').strip()
        category = request.GET.get('category', 'All')
        platforms = request.GET.getlist('platform') 
        # Start with all approved apps
        apps = App.objects.filter(status="Approved")

        # Filter by search query if provided
        if query:
            apps = apps.filter(app_name__icontains=query)

        # Filter by category if it's not 'All'
        if category != 'All':
            apps = apps.filter(category=category)

        # Filter by platform if it's not 'All'
        if platforms:
            # Check if any of the requested platforms match the app's supported platforms
            platform_queries = Q()
            for platform in platforms:
                platform_queries |= Q(supported_platforms__icontains=platform)
            apps = apps.filter(platform_queries)
        # If no apps match the filters, return a message
        # Serialize the filtered results
        serializer = AppSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

class UpdateAppView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = AppSerializer  # Assuming you have an AppSerializer

    def get_queryset(self):
        return App.objects.all()

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if the user is the developer of the app
        if instance.developer != request.user:
            return Response({'detail': 'Access restricted. You are not the developer of this app.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)

            # Handle uploaded screenshots
            screenshots = request.FILES.getlist('screenshots_upload')
            if screenshots:
                Screenshot.objects.filter(app=instance).delete()  # Clear existing screenshots
                for screenshot in screenshots:
                    Screenshot.objects.create(app=instance, screenshot=screenshot)

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


