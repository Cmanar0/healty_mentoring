from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

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
