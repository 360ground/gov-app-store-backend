# apps/urls.py
from django.urls import path
from .views import SubmitNewAppView,AppListView,submitted_apps,DeveloperAppsView,AppDetailView,AppListViewAll,AppDetailViewAll,increment_view_count,AppReviewView,AppSearchView,UpdateAppView, FAQListView


app_name = 'apps'  
urlpatterns = [
    path('app_listing/', AppListViewAll.as_view(), name='app_listing_all'),  
    path('listing/', AppListView.as_view(), name='app_listing'),  
    path('submit/', SubmitNewAppView.as_view(), name='submit_new_app'), 
    path('submitted/', submitted_apps, name='submitted_apps'),
    path('developer_apps/', DeveloperAppsView.as_view(), name='submitted_app_developer'),
    path('listing/<int:id>/', AppDetailView.as_view(), name='app_detail'),
    path('app_listing/<int:id>/', AppDetailViewAll.as_view(), name='app_detail_all'),
    path('increment-view-count/', increment_view_count, name='increment_view_count'),
    path('submit/<int:id>/', SubmitNewAppView.as_view(), name='app_update'),  # For updates
    path('reviews/<int:app_id>/', AppReviewView.as_view(), name='app-reviews'),
    path('search/', AppSearchView.as_view(), name='app-search'),
    path('update/<int:pk>/', UpdateAppView.as_view(), name='update-app'),
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    
]

