from django.contrib import admin
from django import forms
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from .models import Session, Notification, SessionInvitation
from accounts.models import CustomUser, UserProfile, MentorProfile
import uuid

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_datetime', 'end_datetime', 'created_by', 'session_type', 'status', 'session_price', 'expires_at')
    list_filter = ('session_type', 'status', 'start_datetime')
    search_fields = ('note', 'mentors__user__email')
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
            
            # Create a new session with copied fields (no created_by; use session.mentors)
            cloned_session = Session.objects.create(
                start_datetime=session.start_datetime,
                end_datetime=session.end_datetime,
                note=session.note,
                session_type=session.session_type,
                status=cloned_status,
                expires_at=session.expires_at,
                session_price=session.session_price,
                client_first_name=session.client_first_name,
                client_last_name=session.client_last_name,
                tasks=session.tasks.copy() if session.tasks else [],
                previous_data=None,
                changes_requested_by=None,
                original_data=None,
                changed_by=None,
            )
            if attendees:
                cloned_session.attendees.set(attendees)
            for mentor_profile in session.mentors.all():
                mentor_profile.sessions.add(cloned_session)
            
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


class SessionInvitationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'invited_email', 
        'session_link', 
        'mentor_link',
        'expires_at', 
        'session_end_datetime',
        'is_expired_status',
        'created_at',
        'accepted_at',
        'cancelled_at',
        'token_preview'
    )
    list_filter = ('created_at', 'expires_at', 'accepted_at', 'cancelled_at')
    search_fields = ('invited_email', 'token', 'session__id', 'mentor__user__email')
    readonly_fields = ('token', 'created_at', 'last_sent_at', 'expires_at', 'accepted_at', 'cancelled_at', 'is_expired_status', 'session_end_datetime')
    date_hierarchy = 'created_at'
    raw_id_fields = ('session', 'mentor', 'invited_user')
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('token', 'invited_email', 'invited_user', 'created_at', 'last_sent_at')
        }),
        ('Expiration', {
            'fields': ('expires_at', 'session_end_datetime', 'is_expired_status'),
            'description': 'expires_at should match the session end_datetime'
        }),
        ('Status', {
            'fields': ('accepted_at', 'cancelled_at')
        }),
        ('Relations', {
            'fields': ('session', 'mentor')
        }),
    )
    
    def session_link(self, obj):
        """Link to the related session"""
        if obj.session:
            url = f"/admin/general/session/{obj.session.id}/change/"
            return format_html('<a href="{}">Session #{}</a>', url, obj.session.id)
        return '-'
    session_link.short_description = 'Session'
    
    def mentor_link(self, obj):
        """Link to the related mentor"""
        if obj.mentor and obj.mentor.user:
            url = f"/admin/accounts/mentorprofile/{obj.mentor.id}/change/"
            name = f"{obj.mentor.first_name} {obj.mentor.last_name}".strip() or obj.mentor.user.email
            return format_html('<a href="{}">{}</a>', url, name)
        return '-'
    mentor_link.short_description = 'Mentor'
    
    def session_end_datetime(self, obj):
        """Display the session's end_datetime for comparison"""
        if obj.session and obj.session.end_datetime:
            return obj.session.end_datetime
        return '-'
    session_end_datetime.short_description = 'Session End DateTime'
    
    def is_expired_status(self, obj):
        """Display expiration status with color coding"""
        if obj.cancelled_at:
            return format_html('<span style="color: #dc3545;">Cancelled</span>')
        if obj.accepted_at:
            return format_html('<span style="color: #28a745;">Accepted</span>')
        if obj.is_expired():
            return format_html('<span style="color: #dc3545; font-weight: bold;">Expired</span>')
        if obj.expires_at:
            if obj.expires_at < timezone.now():
                return format_html('<span style="color: #dc3545; font-weight: bold;">Expired</span>')
            else:
                return format_html('<span style="color: #28a745;">Active</span>')
        return format_html('<span style="color: #ffc107;">No expiration set</span>')
    is_expired_status.short_description = 'Status'
    
    def token_preview(self, obj):
        """Show a preview of the token"""
        if obj.token:
            return format_html('<code style="font-size: 0.85em;">{}</code>', obj.token[:16] + '...')
        return '-'
    token_preview.short_description = 'Token'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('session', 'mentor', 'mentor__user', 'invited_user')

admin.site.register(SessionInvitation, SessionInvitationAdmin)
