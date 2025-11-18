# from django.contrib import admin
# from .models import App

# @admin.register(App)
# class AppAdmin(admin.ModelAdmin):
#     list_display = ('app_name', 'developer', 'category', 'status', 'created_at')
#     list_filter = ('status', 'category', 'created_at')
#     search_fields = ('app_name', 'developer__username', 'tags')

from django.contrib import admin
from .models import App, Screenshot,Review, FAQ
from django.core.mail import send_mail


class ScreenshotInline(admin.TabularInline):
    model = Screenshot
    extra = 1
class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    fields = ['user', 'rating', 'comment', 'created_at']
    readonly_fields = ['created_at']

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category')
    list_filter = ('category',)
    search_fields = ('question', 'answer')

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_status_change_email(developer_email, app_name, old_status, new_status,developer_name,admin_note):
    # Dynamic message content based on the new status
    if new_status == 'Approved':
        subject = f"Your app {app_name} has been approved"
        html_message = render_to_string('approval_email_templet.html', {
            'app_name': app_name,
            'new_status': new_status,
            'message': "We are excited to inform you that your app submission has been successfully reviewed and approved! Congratulations on reaching this important milestone.",
            'button_text': 'Go to Your Dashboard',
            'button_url': 'http://localhost:3000/developer_portal/appstore',  # Replace with actual dashboard URL
            'developer_name':developer_name,
            'admin_note': admin_note
        })
    elif new_status == 'Rejected':
        subject = f"Your app {app_name} has been rejected"
        html_message = render_to_string('rejection_email_templet.html', {
            'app_name': app_name,
            'new_status': new_status,
            'message': "We regret to inform you that your app submission has been rejected. Please review the feedback and resubmit once the issues are resolved.",
            'button_text': 'Go to Your Dashboard',
            'button_url': 'http://localhost:3000/developer_portal/appstore',  # Replace with actual dashboard URL
            'developer_name':developer_name,
            'admin_note': admin_note

        })
    else:
        subject = f"Your app {app_name} status is pending"
        html_message = render_to_string('pending_email_templet.html', {
            'app_name': app_name,
            'new_status': new_status,
            'message': "Your app submission is under review. We will notify you once the status changes.",
            'button_text': 'Go to Your Dashboard',
            'button_url': 'http://localhost:3000/developer_portal/appstore',  # Replace with actual dashboard URL
            'developer_name':developer_name,
            'admin_note': admin_note
        })
    
    # Send email with HTML content
    send_mail(
        subject,
        strip_tags(html_message),  # Plain text fallback
        'tayeyohanis8@gmail.com',  # Replace with your email address
        [developer_email],  # Send the email to the developer
        fail_silently=False,
        html_message=html_message,  # Send the HTML content
    )


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('app_name', 'developer', 'category', 'status', 'created_at', 
                   'regulation_compliance', 'content_guidelines', 'security_requirements')
    list_filter = ('status', 'category', 'created_at', 
                  'regulation_compliance', 'content_guidelines', 'security_requirements')
    search_fields = ('app_name', 'developer__username', 'tags')
    inlines = [ScreenshotInline, ReviewInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('app_name', 'developer', 'category', 'app_version', 'supported_platforms')
        }),
        ('App Content', {
            'fields': ('description', 'tags', 'privacy_policy_url', 'release_notes')
        }),
        ('Media Files', {
            'fields': ('apk_file', 'app_icon', 'cover_graphics', 'promotional_video')
        }),
        ('Compliance Information', {
            'fields': ('regulation_compliance', 'content_guidelines', 'security_requirements'),
            'description': 'Please check all compliance requirements that have been met.'
        }),
        ('Status Information', {
            'fields': ('status', 'admin_note', 'ios_url', 'web_portal')
        }),
    )

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            old_status = App.objects.get(id=obj.id).status if obj.id else None
            new_status = obj.status
            
            # Send email only if the status has changed
            if old_status != new_status:
                send_status_change_email(
                    developer_email=obj.developer.email,
                    app_name=obj.app_name,
                    old_status=old_status,
                    new_status=new_status,
                    developer_name=obj.developer,
                    admin_note=obj.admin_note
                )
        
        # Call the parent class's save method
        super().save_model(request, obj, form, change)

