from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField
from .validators import validate_apk, validate_icon, validate_cover_graphics, validate_screenshot

class App(models.Model):
    CATEGORY_CHOICES = [
    ('Education', 'Education'),
    ('Finance', 'Finance'),
    ('Health', 'Health'),
    ('Agriculture', 'Agriculture'),
    ('Trade', 'Trade'),
    ('Technology', 'Technology'),
    ('Social Affairs', 'Social Affairs'),
    ('Justice', 'Justice'),
    ('Logistics', 'Logistics'),     
    ]
    
    PLATFORM_CHOICES = [('Android', 'Android'),('IOS', 'IOS')]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Unpublished', 'Unpublished'),

    ]

    developer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=255)
    app_version = models.CharField(max_length=20)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)  
    supported_platforms = MultiSelectField(choices=PLATFORM_CHOICES)  
    apk_file = models.FileField(upload_to='apk_files/')
    app_icon = models.ImageField(upload_to='icons/')
    cover_graphics = models.ImageField(upload_to='covers/')
    # screenshots = models.ImageField(upload_to='screenshots/')
    promotional_video = models.FileField(upload_to='videos/', blank=True, null=True)
    description = models.TextField(max_length=100000)
    tags = models.CharField(max_length=255)
    privacy_policy_url = models.URLField()
    release_notes = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    ios_url = models.URLField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True) # Admin note for approval/rejection
    web_portal = models.URLField(blank=True, null=True)
    view_count = models.IntegerField(default=0)
    
    # Compliance checkboxes
    regulation_compliance = models.BooleanField(default=False, verbose_name="Regulation Compliance")
    content_guidelines = models.BooleanField(default=False, verbose_name="Content Guidelines")
    security_requirements = models.BooleanField(default=False, verbose_name="Security Requirements")
    
    def __str__(self):
        return self.app_name
    
class Screenshot(models.Model):
    app = models.ForeignKey(App, related_name='screenshots', on_delete=models.CASCADE)
    screenshot = models.ImageField(upload_to='screenshots/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.app.app_name} - Screenshot {self.id}"
    

class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ('Platform', 'Platform'),
        ('Citizen', 'Citizen'),
        ('Developer', 'Developer'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    question = models.TextField()
    answer = models.TextField()
    # is_active = models.BooleanField(default=True, help_text="Uncheck this to hide the FAQ without deleting it.")
    # display_order = models.PositiveIntegerField(default=0, help_text="FAQS with a lower number will appear first.")

    class Meta:
        ordering = ['category', 'question']
    
    def __str__(self):
        return self.question 
    
class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    app = models.ForeignKey(App, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user} for {self.app.app_name}"
