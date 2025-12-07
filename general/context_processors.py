from .models import Notification

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

