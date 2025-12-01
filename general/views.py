from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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
