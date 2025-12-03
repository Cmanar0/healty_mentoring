from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from dashboard_mentor.constants import COMMON_TIMEZONES
import json

@login_required
def index(request):
    # Dispatcher view: redirects to the appropriate dashboard based on role
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'mentor':
            return redirect('/dashboard/mentor/')
        elif request.user.profile.role == 'user':
            return redirect('/dashboard/user/')
        elif request.user.profile.role == 'admin':
            # Admin might go to Django admin or a specific admin dashboard
            return redirect('/admin/') 
    
    # Fallback if no profile or role
    return redirect('web:landing')

@login_required
@require_POST
def mark_manual_displayed(request):
    """Mark a manual as displayed and remove it from the array"""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'error': 'No profile found'}, status=400)
    
    try:
        data = json.loads(request.body)
        manual_id = data.get('manual_id')
        
        if not manual_id:
            return JsonResponse({'error': 'manual_id is required'}, status=400)
        
        profile = request.user.profile
        manuals = profile.manuals if profile.manuals else []
        
        # Remove the manual with the given ID
        profile.manuals = [m for m in manuals if m.get('id') != manual_id]
        profile.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def update_timezone(request):
    """Update user's timezone via AJAX - works for both mentor and user profiles"""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'success': False, 'error': 'No profile found'}, status=400)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'update_detected', 'update_selected', 'confirm_mismatch'
        
        profile = request.user.profile
        
        if action == 'update_detected':
            # Update detected timezone (called on every page load)
            detected_timezone = data.get('detected_timezone', '').strip()
            if detected_timezone:
                profile.detected_timezone = detected_timezone
                # If selected_timezone matches old detected, update it too
                if profile.selected_timezone == profile.detected_timezone:
                    profile.selected_timezone = detected_timezone
                # If they match now, clear confirmed mismatch
                if profile.selected_timezone == detected_timezone:
                    profile.confirmed_timezone_mismatch = False
                profile.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Detected timezone updated',
                    'detected_timezone': detected_timezone,
                    'selected_timezone': profile.selected_timezone,
                    'confirmed_mismatch': profile.confirmed_timezone_mismatch
                })
        
        elif action == 'update_selected':
            # Update selected timezone and handle mismatch confirmation
            selected_timezone = data.get('selected_timezone', '').strip()
            confirmed_mismatch = data.get('confirmed_mismatch', False)
            
            # If selected_timezone is empty, use detected_timezone
            if not selected_timezone and profile.detected_timezone:
                selected_timezone = profile.detected_timezone
            
            if not selected_timezone:
                return JsonResponse({'success': False, 'error': 'Timezone is required'}, status=400)
            
            profile.selected_timezone = selected_timezone
            profile.confirmed_timezone_mismatch = confirmed_mismatch
            
            # If selected matches detected, clear confirmed mismatch
            if profile.selected_timezone == profile.detected_timezone:
                profile.confirmed_timezone_mismatch = False
            
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Selected timezone updated',
                'selected_timezone': selected_timezone,
                'confirmed_mismatch': confirmed_mismatch
            })
        
        elif action == 'use_detected':
            # User chose to use detected timezone
            detected_timezone = data.get('detected_timezone', '').strip()
            if not detected_timezone:
                return JsonResponse({'success': False, 'error': 'Detected timezone is required'}, status=400)
            
            profile.detected_timezone = detected_timezone
            profile.selected_timezone = detected_timezone
            profile.confirmed_timezone_mismatch = False
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Timezone updated to detected timezone',
                'detected_timezone': detected_timezone,
                'selected_timezone': detected_timezone
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
