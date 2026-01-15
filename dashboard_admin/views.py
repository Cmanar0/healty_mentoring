from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Q
from functools import wraps
from general.models import Notification
from accounts.models import CustomUser
import uuid

def admin_required(view_func):
    """Decorator to ensure only admin users can access admin dashboard pages"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        # Check if user has admin profile
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            # Log out non-admin users trying to access admin pages
            logout(request)
            messages.error(request, "You do not have permission to access this page.")
            return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def dashboard(request):
    """Admin dashboard home page"""
    return render(request, 'dashboard_admin/dashboard.html', {
        'debug': settings.DEBUG,
    })

@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def notifications(request):
    """Admin notifications page - create and list notifications"""
    # Handle notification creation
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            target_type = request.POST.get('target_type')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not title or not description:
                messages.error(request, 'Title and description are required.')
                return redirect('general:dashboard_admin:notifications')
            
            # Generate batch ID for this notification creation
            batch_id = uuid.uuid4()
            created_count = 0
            
            if target_type == 'all':
                # Send to all users
                users = CustomUser.objects.filter(is_active=True)
                for user in users:
                    Notification.objects.create(
                        user=user,
                        batch_id=batch_id,
                        target_type=target_type,
                        title=title,
                        description=description
                    )
                    created_count += 1
                    
            elif target_type == 'all_users':
                # Send to all users with 'user' role
                users = CustomUser.objects.filter(
                    is_active=True,
                    user_profile__isnull=False
                )
                for user in users:
                    Notification.objects.create(
                        user=user,
                        batch_id=batch_id,
                        target_type=target_type,
                        title=title,
                        description=description
                    )
                    created_count += 1
                    
            elif target_type == 'all_mentors':
                # Send to all users with 'mentor' role
                users = CustomUser.objects.filter(
                    is_active=True,
                    mentor_profile__isnull=False
                )
                for user in users:
                    Notification.objects.create(
                        user=user,
                        batch_id=batch_id,
                        target_type=target_type,
                        title=title,
                        description=description
                    )
                    created_count += 1
                    
            elif target_type == 'single':
                # Send to a single user
                user_id = request.POST.get('user_id')
                if not user_id:
                    messages.error(request, 'Please select a user.')
                    return redirect('general:dashboard_admin:notifications')
                
                try:
                    user = CustomUser.objects.get(id=user_id, is_active=True)
                    Notification.objects.create(
                        user=user,
                        batch_id=batch_id,
                        target_type=target_type,
                        title=title,
                        description=description
                    )
                    created_count = 1
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Selected user not found.')
                    return redirect('general:dashboard_admin:notifications')
            
            messages.success(request, f'Successfully created {created_count} notification(s).')
            return redirect('general:dashboard_admin:notifications')
    
    # Group notifications by batch_id - get unique batches
    from django.db.models import Count, Min, Q
    
    # Start with all notifications
    all_notifications = Notification.objects.all()
    
    # Search functionality - filter notifications first, then group by batch
    search_query = request.GET.get('search', '').strip()
    if search_query:
        all_notifications = all_notifications.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Get unique batch_ids from filtered notifications
    batch_ids = all_notifications.values_list('batch_id', flat=True).distinct()
    
    # Get batch aggregates - group by batch_id and get stats
    from django.db.models import F, Subquery, OuterRef
    batch_notifications = Notification.objects.filter(
        batch_id__in=batch_ids
    ).values('batch_id', 'target_type').annotate(
        created_at=Min('created_at'),
        total_count=Count('id'),
        read_count=Count('id', filter=Q(is_opened=True)),
        unread_count=Count('id', filter=Q(is_opened=False)),
        user_count=Count('user', distinct=True),
        user_role_count=Count('user', distinct=True, filter=Q(user__user_profile__isnull=False)),
        mentor_role_count=Count('user', distinct=True, filter=Q(user__mentor_profile__isnull=False)),
    ).order_by('-created_at')
    
    # Filter by target_type
    target_filter = request.GET.get('target_type', '')
    if target_filter:
        batch_notifications = batch_notifications.filter(target_type=target_filter)
    
    # Get title and description for each batch (they're the same for all notifications in a batch)
    batches_list = []
    for batch in batch_notifications:
        # Get first notification from batch to get title/description
        first_notification = Notification.objects.filter(batch_id=batch['batch_id']).first()
        if first_notification:
            batch['title'] = first_notification.title
            batch['description'] = first_notification.description
            # target_type is already in batch from the values() call
            batches_list.append(batch)
    
    # Get total count before pagination
    total_count = len(batches_list)
    
    # Manual pagination for batches
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(batches_list, 20)  # 20 batches per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Get user count for each role
    total_users = CustomUser.objects.filter(is_active=True).count()
    user_count = CustomUser.objects.filter(is_active=True, user_profile__isnull=False).count()
    mentor_count = CustomUser.objects.filter(is_active=True, mentor_profile__isnull=False).count()
    
    # Get filter values for template
    current_filters = {
        'search': search_query,
        'target_type': target_filter,
    }
    
    return render(request, 'dashboard_admin/notifications.html', {
        'debug': settings.DEBUG,
        'batches': page_obj,
        'page_obj': page_obj,
        'total_users': total_users,
        'user_count': user_count,
        'mentor_count': mentor_count,
        'total_count': total_count,
        'filters': current_filters,
    })


@login_required
@admin_required
@require_POST
def notification_delete(request, batch_id):
    """Delete all notifications in a batch"""
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError:
        messages.error(request, 'Invalid batch ID.')
        return redirect('general:dashboard_admin:notifications')
    
    # Get all notifications in this batch
    notifications_in_batch = Notification.objects.filter(batch_id=batch_uuid)
    count = notifications_in_batch.count()
    
    if count == 0:
        messages.error(request, 'Batch not found.')
        return redirect('general:dashboard_admin:notifications')
    
    # Delete all notifications in the batch
    notifications_in_batch.delete()
    messages.success(request, f'Successfully deleted {count} notification(s) from batch.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'deleted_count': count})
    
    return redirect('general:dashboard_admin:notifications')


@login_required
@admin_required
def notification_search_users(request):
    """Search users for autocomplete in notification form"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search by email, first name, or last name
    users = CustomUser.objects.filter(
        is_active=True
    ).filter(
        Q(email__icontains=query) |
        Q(user_profile__first_name__icontains=query) |
        Q(user_profile__last_name__icontains=query) |
        Q(mentor_profile__first_name__icontains=query) |
        Q(mentor_profile__last_name__icontains=query)
    )[:10]  # Limit to 10 results
    
    results = []
    for user in users:
        profile = user.profile
        if profile:
            name = f"{profile.first_name} {profile.last_name}"
            role = profile.role
        else:
            name = user.email
            role = 'unknown'
        
        results.append({
            'id': user.id,
            'email': user.email,
            'name': name,
            'role': role
        })
    
    return JsonResponse({'users': results})

@login_required
@admin_required
def blog(request):
    """Admin blog management page"""
    return render(request, 'dashboard_admin/blog.html', {
        'debug': settings.DEBUG,
    })

@login_required
@admin_required
def tickets(request):
    """Admin tickets/support page"""
    return render(request, 'dashboard_admin/tickets.html', {
        'debug': settings.DEBUG,
    })

@login_required
@admin_required
def statistics(request):
    """Admin statistics page"""
    return render(request, 'dashboard_admin/statistics.html', {
        'debug': settings.DEBUG,
    })
