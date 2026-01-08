from django.contrib import admin
from django import forms
from django.contrib import messages
from django.utils.html import format_html
from .models import Session, Notification
from accounts.models import CustomUser, UserProfile, MentorProfile
import uuid

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_datetime', 'end_datetime', 'created_by', 'session_type', 'status', 'session_price', 'expires_at')
    list_filter = ('session_type', 'status', 'start_datetime')
    search_fields = ('created_by__email', 'note')
    filter_horizontal = ('attendees',)
    actions = ['clone_session']
    
    def clone_session(self, request, queryset):
        """Admin action to clone selected sessions"""
        cloned_count = 0
        for session in queryset:
            # Get attendees before cloning (ManyToMany field)
            attendees = list(session.attendees.all())
            
            # Preserve original status if it was invited or confirmed, otherwise set to draft
            # This ensures that if the cloned session is moved to the past,
            # cleanup will transition it to expired/completed instead of deleting it
            original_status = session.status
            if original_status in ['invited', 'confirmed']:
                cloned_status = original_status
            else:
                cloned_status = 'draft'
            
            # Create a new session with copied fields
            cloned_session = Session.objects.create(
                start_datetime=session.start_datetime,
                end_datetime=session.end_datetime,
                created_by=session.created_by,
                note=session.note,
                session_type=session.session_type,
                status=cloned_status,
                expires_at=session.expires_at,
                session_price=session.session_price,
                client_first_name=session.client_first_name,
                client_last_name=session.client_last_name,
                tasks=session.tasks.copy() if session.tasks else [],
                # Reset change tracking fields
                previous_data=None,
                changes_requested_by=None,
                original_data=None,
                changed_by=None,
            )
            
            # Add attendees to cloned session
            if attendees:
                cloned_session.attendees.set(attendees)
            
            # Add to mentor profile if the creator has a mentor profile
            try:
                if hasattr(session.created_by, 'mentor_profile'):
                    session.created_by.mentor_profile.sessions.add(cloned_session)
            except Exception:
                pass
            
            cloned_count += 1
        
        self.message_user(
            request,
            f'Successfully cloned {cloned_count} session(s). Cloned sessions preserve original status (invited/confirmed) or are set to "draft".',
            messages.SUCCESS
        )
    clone_session.short_description = 'Clone selected sessions'

admin.site.register(Session, SessionAdmin)


class NotificationCreationForm(forms.Form):
    """Custom form for creating notifications"""
    TARGET_CHOICES = [
        ('single', 'Single User'),
        ('all_users', 'All User Profiles'),
        ('all_mentors', 'All Mentor Profiles'),
    ]
    
    target_type = forms.ChoiceField(
        choices=TARGET_CHOICES,
        widget=forms.RadioSelect,
        initial='single',
        label='Target Audience'
    )
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(),
        required=False,
        label='Select User',
        help_text='Required when "Single User" is selected'
    )
    title = forms.CharField(max_length=200, required=True)
    description = forms.CharField(widget=forms.Textarea, required=True)
    
    def clean(self):
        cleaned_data = super().clean()
        target_type = cleaned_data.get('target_type')
        user = cleaned_data.get('user')
        
        if target_type == 'single' and not user:
            raise forms.ValidationError('Please select a user when targeting a single user.')
        
        return cleaned_data


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_opened', 'created_at', 'batch_id_display')
    list_filter = ('is_opened', 'created_at', 'batch_id')
    search_fields = ('title', 'description', 'user__email')
    readonly_fields = ('batch_id', 'created_at')
    date_hierarchy = 'created_at'
    actions = ['delete_batch']
    
    def batch_id_display(self, obj):
        """Display batch ID with count of notifications in batch"""
        count = Notification.objects.filter(batch_id=obj.batch_id).count()
        return format_html(
            '<span style="font-family: monospace;">{}</span> <span style="color: #666;">({} notifications)</span>',
            str(obj.batch_id)[:8] + '...',
            count
        )
    batch_id_display.short_description = 'Batch ID'
    
    def delete_batch(self, request, queryset):
        """Admin action to delete all notifications in the same batch"""
        deleted_count = 0
        batch_ids = set()
        
        for notification in queryset:
            if notification.batch_id not in batch_ids:
                batch_notifications = Notification.objects.filter(batch_id=notification.batch_id)
                count = batch_notifications.count()
                batch_notifications.delete()
                deleted_count += count
                batch_ids.add(notification.batch_id)
        
        self.message_user(
            request,
            f'Successfully deleted {deleted_count} notification(s) from {len(batch_ids)} batch(es).',
            messages.SUCCESS
        )
    delete_batch.short_description = 'Delete all notifications in selected batch(es)'
    
    def has_add_permission(self, request):
        """Disable standard add permission - use custom view instead"""
        return False
    
    def get_urls(self):
        """Add custom URLs for notification creation"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('create/', self.admin_site.admin_view(self.create_notification_view), name='general_notification_create'),
        ]
        return custom_urls + urls
    
    def create_notification_view(self, request):
        """Custom view for creating notifications"""
        from django.shortcuts import render, redirect
        from django.contrib.admin import site
        
        if request.method == 'POST':
            form = NotificationCreationForm(request.POST)
            if form.is_valid():
                target_type = form.cleaned_data['target_type']
                title = form.cleaned_data['title']
                description = form.cleaned_data['description']
                
                # Generate a single batch_id for all notifications created in this action
                batch_id = uuid.uuid4()
                notifications_created = 0
                
                if target_type == 'single':
                    user = form.cleaned_data['user']
                    Notification.objects.create(
                        user=user,
                        batch_id=batch_id,
                        title=title,
                        description=description
                    )
                    notifications_created = 1
                elif target_type == 'all_users':
                    # Get all users with UserProfile
                    users = CustomUser.objects.filter(user_profile__isnull=False).distinct()
                    for user in users:
                        Notification.objects.create(
                            user=user,
                            batch_id=batch_id,
                            title=title,
                            description=description
                        )
                        notifications_created += 1
                elif target_type == 'all_mentors':
                    # Get all users with MentorProfile
                    users = CustomUser.objects.filter(mentor_profile__isnull=False).distinct()
                    for user in users:
                        Notification.objects.create(
                            user=user,
                            batch_id=batch_id,
                            title=title,
                            description=description
                        )
                        notifications_created += 1
                
                messages.success(
                    request,
                    f'Successfully created {notifications_created} notification(s) with batch ID: {batch_id}'
                )
                return redirect('admin:general_notification_changelist')
        else:
            form = NotificationCreationForm()
        
        context = {
            **site.each_context(request),
            'title': 'Create Notification',
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        return render(request, 'admin/general/notification/create_notification.html', context)

admin.site.register(Notification, NotificationAdmin)
