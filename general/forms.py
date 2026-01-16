from django import forms
from .models import Ticket, TicketComment, BlogPost
from dashboard_mentor.constants import PREDEFINED_CATEGORIES

class TicketForm(forms.ModelForm):
    """Form for submitting support tickets"""
    image = forms.ImageField(
        required=False,
        help_text="Optional: Upload an image (max 5MB)",
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control',
        })
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a brief title for your issue',
                'maxlength': '200',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your issue in detail...',
            }),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (5MB = 5 * 1024 * 1024 bytes)
            max_size = 5 * 1024 * 1024
            if image.size > max_size:
                raise forms.ValidationError("Image size must be less than 5MB.")
        return image


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets"""
    image = forms.ImageField(
        required=False,
        help_text="Optional: Upload an image (max 5MB)",
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control',
            'id': 'comment-image-input',
        })
    )
    
    class Meta:
        model = TicketComment
        fields = ['comment', 'image']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add your comment...',
            }),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (5MB = 5 * 1024 * 1024 bytes)
            max_size = 5 * 1024 * 1024
            if image.size > max_size:
                raise forms.ValidationError("Image size must be less than 5MB.")
        return image


# Cover color options that match the app styling
BLOG_COVER_COLORS = [
    ('#10b981', 'Green (Primary)'),
    ('#059669', 'Green Dark'),
    ('#3b82f6', 'Blue'),
    ('#2563eb', 'Blue Dark'),
    ('#8b5cf6', 'Purple'),
    ('#7c3aed', 'Purple Dark'),
    ('#f59e0b', 'Amber'),
    ('#d97706', 'Amber Dark'),
    ('#ef4444', 'Red'),
    ('#dc2626', 'Red Dark'),
    ('#06b6d4', 'Cyan'),
    ('#0891b2', 'Cyan Dark'),
    ('#ec4899', 'Pink'),
    ('#db2777', 'Pink Dark'),
]


class BlogPostForm(forms.ModelForm):
    """Form for creating and editing blog posts"""
    cover_image = forms.ImageField(
        required=False,
        help_text="Optional: Upload a cover image (max 5MB, JPG/PNG/WEBP)",
        widget=forms.FileInput(attrs={
            'accept': 'image/jpeg,image/jpg,image/png,image/webp',
            'class': 'form-control',
            'id': 'cover-image-input',
        })
    )
    
    categories = forms.MultipleChoiceField(
        choices=[(cat['id'], cat['name']) for cat in PREDEFINED_CATEGORIES],
        required=False,
        help_text="Select one or more categories",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'category-checkboxes',
        })
    )
    
    class Meta:
        model = BlogPost
        fields = ['title', 'excerpt', 'content', 'cover_image', 'categories', 'seo_tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter blog post title',
                'maxlength': '200',
                'required': True,
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: Short excerpt for preview (max 500 characters)',
                'maxlength': '500',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 20,
                'placeholder': 'Write your blog post content here...',
                'id': 'blog-content-editor',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial cover color if it's a new post (randomly select from colors)
        # Set initial categories if editing
        if self.instance.pk and self.instance.categories:
            self.fields['categories'].initial = self.instance.categories
        
        # Set initial SEO tags if editing
        if self.instance.pk and self.instance.seo_tags:
            import json
            self.fields['seo_tags'].initial = json.dumps(self.instance.seo_tags)
    
    def clean_cover_image(self):
        cover_image = self.cleaned_data.get('cover_image')
        if cover_image:
            # Check file size (5MB = 5 * 1024 * 1024 bytes)
            max_size = 5 * 1024 * 1024
            if cover_image.size > max_size:
                raise forms.ValidationError("Cover image size must be less than 5MB.")
        return cover_image
    
    def clean_categories(self):
        categories = self.cleaned_data.get('categories', [])
        # Validate that all selected categories exist in PREDEFINED_CATEGORIES
        valid_category_ids = [cat['id'] for cat in PREDEFINED_CATEGORIES]
        invalid_categories = [cat for cat in categories if cat not in valid_category_ids]
        if invalid_categories:
            raise forms.ValidationError(f"Invalid categories: {', '.join(invalid_categories)}")
        return list(categories)  # Return as list for JSONField
    
    def clean_seo_tags(self):
        seo_tags = self.cleaned_data.get('seo_tags', '[]')
        # The hidden input sends a JSON string, so parse it
        import json
        try:
            if isinstance(seo_tags, str):
                seo_tags = json.loads(seo_tags) if seo_tags else []
            # Ensure it's a list of strings
            if not isinstance(seo_tags, list):
                seo_tags = [seo_tags] if seo_tags else []
            # Filter out empty strings and ensure all are strings
            seo_tags = [str(tag).strip() for tag in seo_tags if tag and str(tag).strip()]
            return seo_tags
        except (json.JSONDecodeError, TypeError):
            return []

