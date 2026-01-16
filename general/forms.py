from django import forms
from .models import Ticket, TicketComment

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

