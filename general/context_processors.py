from .models import Notification, Session, SessionInvitation

def notifications(request):
    """Context processor to provide notifications to all templates"""
    if request.user.is_authenticated:
        # Get latest 5 notifications for dropdown
        latest_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Get unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_opened=False
        ).count()
        
        return {
            'latest_notifications': latest_notifications,
            'unread_count': unread_count,
        }
    return {
        'latest_notifications': [],
        'unread_count': 0,
    }

def pending_sessions_count(request):
    """Context processor to provide pending session count for user dashboard"""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'user':
        user_email = (request.user.email or '').strip().lower()
        
        # Get all pending invitations for this user
        invitations = SessionInvitation.objects.filter(
            invited_email=user_email,
            cancelled_at__isnull=True,
            accepted_at__isnull=True,
            session__status__in=['invited', 'confirmed']
        ).values_list('session_id', flat=True)
        
        invitation_session_ids = set(invitations)
        
        # Get all sessions where user is an attendee
        attendee_sessions = Session.objects.filter(attendees=request.user).values_list('id', flat=True)
        attendee_session_ids = set(attendee_sessions)
        
        # Combine all session IDs
        all_user_session_ids = invitation_session_ids | attendee_session_ids
        
        # Get all sessions with pending changes
        changed_sessions_count = 0
        if all_user_session_ids:
            all_user_sessions = Session.objects.filter(id__in=all_user_session_ids)
            
            for session in all_user_sessions:
                # Skip expired sessions
                if session.status == 'expired':
                    continue
                
                # Skip sessions that are 'invited' and have an active invitation
                if session.status == 'invited' and session.id in invitation_session_ids:
                    continue
                
                # Check for pending changes
                has_pending_change = (
                    (session.previous_data and session.changes_requested_by == 'mentor') or
                    (session.original_data and session.changed_by == 'mentor')
                )
                
                if has_pending_change:
                    changed_sessions_count += 1
        
        pending_count = len(invitation_session_ids) + changed_sessions_count
        
        return {
            'pending_sessions_count': pending_count,
        }
    return {
        'pending_sessions_count': 0,
    }

