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
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    if profile is not None and profile.role == 'user':
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

def unresolved_tickets_count(request):
    """Context processor to provide unresolved tickets count for admin dashboard"""
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    if profile is not None and profile.role == 'admin':
        from .models import Ticket
        unresolved_count = Ticket.objects.filter(status__in=['submitted', 'in_progress']).count()
        return {
            'unresolved_tickets_count': unresolved_count,
        }
    return {
        'unresolved_tickets_count': 0,
    }

def mentor_ai_coins(request):
    """Context processor to provide mentor AI coins for navbar (mentor dashboard only)."""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile is not None and profile.role == 'mentor':
            mentor_profile = getattr(request.user, 'mentor_profile', None)
            if mentor_profile is not None:
                return {'mentor_ai_coins': getattr(mentor_profile, 'ai_coins', 0)}
    return {'mentor_ai_coins': 0}


def pending_project_assignments(request):
    """
    Context processor to provide pending project assignments count for user dashboard.
    Similar to pending_sessions_count context processor.
    """
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    if profile is not None and profile.role == 'user':
        from dashboard_user.models import Project
        from accounts.models import UserProfile
        
        try:
            user_profile = request.user.user_profile
            count = Project.objects.filter(
                project_owner=user_profile,
                assignment_status='assigned'  # 'assigned' means mentor assigned, awaiting client acceptance
            ).count()
            return {'pending_projects_count': count}
        except Exception:
            return {'pending_projects_count': 0}
    return {'pending_projects_count': 0}
