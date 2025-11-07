from rest_framework import serializers
from .models import App,Screenshot


from rest_framework import serializers
from .models import App, Screenshot, Review

# Screenshot Serializer
class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ['id', 'screenshot', 'created_at']

# Review Serializer
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # To show the user's username or custom display value
    
    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'user', 'created_at']

# App Serializer
class AppSerializer(serializers.ModelSerializer):
    screenshots = ScreenshotSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)  # Added reviews field
    class Meta:
        model = App
        fields = '__all__'


# class AppSubmissionSerializer(serializers.ModelSerializer):
#     screenshots = ScreenshotSerializer(many=True, read_only=True)
#     class Meta:
#         model = App
#         fields = [
#             'app_name', 'app_version', 'category', 'supported_platforms', 'apk_file',
#             'app_icon', 'cover_graphics','promotional_video',
#             'description', 'tags', 'privacy_policy_url', 'release_notes','screenshots','ios_url'
#         ]


# class AppSubmissionSerializer(serializers.ModelSerializer):
#     screenshots = ScreenshotSerializer(many=True, read_only=True)
#     screenshots_upload = serializers.ListField(
#         child=serializers.ImageField(), write_only=True, required=False
#     )

#     class Meta:
#         model = App
#         fields = [
#             'app_name', 'app_version', 'category', 'supported_platforms', 'apk_file',
#             'app_icon', 'cover_graphics', 'promotional_video', 'description', 
#             'tags', 'privacy_policy_url', 'release_notes', 'ios_url', 'screenshots', 'screenshots_upload'
#         ]

#     def create(self, validated_data):
#         screenshots_data = validated_data.pop('screenshots_upload', [])
#         app = App.objects.create(**validated_data)
#         for screenshot_data in screenshots_data:
#             Screenshot.objects.create(app=app, screenshot=screenshot_data)
class AppSubmissionSerializer(serializers.ModelSerializer):
    screenshots_upload = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    
    # ✅ Special handling for supported_platforms
    supported_platforms = serializers.ListField(
        child=serializers.ChoiceField(choices=App.PLATFORM_CHOICES),
        allow_empty=False,
        write_only=False
    )

    class Meta:
        model = App
        fields = [
            'app_name', 'app_version', 'category', 'supported_platforms',
            'apk_file', 'app_icon', 'cover_graphics', 'promotional_video',
            'description', 'tags', 'privacy_policy_url', 'release_notes',
            'ios_url', 'screenshots_upload','web_portal','admin_note'
        ]

    # ✅ FIXED: Handle MultiSelectField without copying data
    def to_internal_value(self, data):
        # Handle supported_platforms WITHOUT copying the entire data
        if hasattr(data, 'getlist') and 'supported_platforms' in data:
            platforms = data.getlist('supported_platforms')
            platforms = [p for p in platforms if p.strip()]
            if platforms:
                # Store processed platforms for later use
                self._processed_platforms = platforms
        
        # Call parent to get the validated data
        validated_data = super().to_internal_value(data)
        
        # Override supported_platforms with our processed version
        if hasattr(self, '_processed_platforms'):
            validated_data['supported_platforms'] = self._processed_platforms
        
        return validated_data

    def create(self, validated_data):
        screenshots_data = validated_data.pop('screenshots_upload', [])
        
        # ✅ Handle supported_platforms properly  
        supported_platforms = validated_data.get('supported_platforms', [])
        if supported_platforms:
            # Ensure it's a list and convert to the format MultiSelectField expects
            if isinstance(supported_platforms, list):
                validated_data['supported_platforms'] = supported_platforms
        
        app = App.objects.create(**validated_data)
        
        for screenshot in screenshots_data:
            Screenshot.objects.create(app=app, screenshot=screenshot)
        return app