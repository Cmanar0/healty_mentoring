from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.views import View
from django.contrib import messages
from django.contrib.auth.views import LoginView as BaseLoginView, PasswordResetConfirmView as BasePasswordResetConfirmView, LogoutView as BaseLogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from .forms import RegisterForm, CustomAuthenticationForm
from .models import CustomUser, UserProfile, MentorProfile, MentorClientRelationship
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_POST
from general.email_service import EmailService
import os
import json

class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("general:index")
        form = RegisterForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            print("DEBUG: Form is valid. Creating user...")
            try:
                email = form.cleaned_data["email"].lower()
                password = form.cleaned_data["password1"]
                first_name = form.cleaned_data["first_name"]
                last_name = form.cleaned_data["last_name"]
                role = form.cleaned_data["role"]
                
                # Create user
                user = CustomUser.objects.create_user(email=email, password=password)
                print(f"DEBUG: User {email} created successfully.")
                
                # Default manuals data for navigation tutorial
                default_manuals = [
                    {
                        "id": "createNewSection",
                        "title": "Create New Content",
                        "text": "Use these buttons to quickly create sessions, users, projects, marketing materials, and blog posts.",
                        "position": {"x": -350, "y": 0},
                        "displayed": False
                    },
                    {
                        "id": "statsCard",
                        "title": "Track Your Performance",
                        "text": "View your statistics and metrics here. Use the dropdown to filter by different time periods.",
                        "position": {"x": 0, "y": 300},
                        "displayed": False
                    },
                    {
                        "id": "backlogCard",
                        "title": "Your Backlog",
                        "text": "Items that require your action are displayed here. Stay on top of your tasks!",
                        "position": {"x": 0, "y": -180},
                        "displayed": False
                    }
                ]
                
                # Auto-detect timezone from request headers (if available) or use UTC as fallback
                # Note: This is a best-effort approach. JavaScript will detect the actual browser timezone
                # and the timezone checker will prompt to update if different
                detected_timezone = None
                try:
                    # Try to get timezone from Accept-Language or other headers
                    # For now, we'll let JavaScript handle the detection on first login
                    # But we could use a geolocation API here if needed
                    pass
                except:
                    pass
                
                # Create appropriate profile based on role
                if role == 'mentor':
                    MentorProfile.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        role='mentor',
                        manuals=default_manuals,
                        # time_zone will be auto-detected by JavaScript on first login
                        # and saved via the timezone checker modal
                    )
                    print(f"DEBUG: MentorProfile created for {email}.")
                else:  # role == 'user'
                    UserProfile.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        role='user',
                        manuals=default_manuals,
                        # time_zone will be auto-detected by JavaScript on first login
                        # and saved via the timezone checker modal
                    )
                    print(f"DEBUG: UserProfile created for {email}.")
                
                # Send verification email
                print("DEBUG: Attempting to send verification email...")
                try:
                    send_verification_email(request, user)
                    print("DEBUG: Email sent successfully.")
                except Exception as e:
                    print(f"ERROR: Failed to send verification email: {e}")
                    # Still show success page, but log the error
                    # User can request resend if needed
                
                return render(request, "accounts/email_verify_sent.html", {"email": email})
            except Exception as e:
                print(f"ERROR during registration: {e}")
                # If user was created but email failed, we might want to delete the user or warn
                # For now, just show the error on the form
                form.add_error(None, f"Registration failed: {e}")
        else:
            print("DEBUG: Form is invalid.")
            print(form.errors)
            
        return render(request, "accounts/register.html", {"form": form})

def send_verification_email(request, user):
    """Send email verification email using the universal email service."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # Get domain using EmailService helper
    domain = EmailService.get_site_domain()
    verify_url = f"{domain}{reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})}"
    
    # Use the universal email service
    EmailService.send_verification_email(user, verify_url)

class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            user = None
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.is_email_verified = True
            user.save()
            
            # Send welcome email
            try:
                EmailService.send_welcome_email(user)
            except Exception as e:
                print(f"Error sending welcome email: {e}")
                
            return render(request, "accounts/verify_success.html")
        else:
            return HttpResponse("Invalid verification link", status=400)

import random
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import time

@login_required
@require_POST
def initiate_email_change(request):
    """
    Initiate email change process: generate OTP and send to new email.
    """
    try:
        data = json.loads(request.body)
        new_email = data.get('new_email', '').strip().lower()
        
        if not new_email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
            
        if new_email == request.user.email:
            return JsonResponse({'success': False, 'error': 'New email must be different from current email'}, status=400)
            
        # new_email is already normalized to lowercase in line 169
        if CustomUser.objects.filter(email=new_email).exists():
            return JsonResponse({'success': False, 'error': 'This email is already in use'}, status=400)
            
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store in session with expiry (10 minutes)
        request.session['email_change_otp'] = otp
        request.session['email_change_new_email'] = new_email
        request.session['email_change_expiry'] = time.time() + 600  # 10 minutes
        
        # Send email with error handling
        try:
            email_sent = EmailService.send_email_change_otp(request.user, new_email, otp)
            if not email_sent:
                return JsonResponse({'success': False, 'error': 'Failed to send verification email. Please try again.'}, status=500)
        except Exception as email_error:
            # Log the error but don't expose details to user
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending email change OTP: {str(email_error)}")
            return JsonResponse({'success': False, 'error': 'Failed to send verification email. Please check your email settings and try again.'}, status=500)
        
        return JsonResponse({'success': True, 'message': 'Verification code sent'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def verify_email_change(request):
    """
    Verify OTP and update email.
    """
    try:
        data = json.loads(request.body)
        otp = data.get('otp', '').strip()
        
        if not otp:
            return JsonResponse({'success': False, 'error': 'OTP is required'}, status=400)
            
        session_otp = request.session.get('email_change_otp')
        session_email = request.session.get('email_change_new_email')
        session_expiry = request.session.get('email_change_expiry')
        
        if not session_otp or not session_email or not session_expiry:
            return JsonResponse({'success': False, 'error': 'No pending email change request'}, status=400)
            
        if time.time() > session_expiry:
            return JsonResponse({'success': False, 'error': 'Verification code expired'}, status=400)
            
        if otp != session_otp:
            return JsonResponse({'success': False, 'error': 'Invalid verification code'}, status=400)
            
        # Update email
        user = request.user
        user.email = session_email
        user.is_email_verified = True  # Email is verified when OTP is confirmed
        user.save()
        
        # Clear session
        del request.session['email_change_otp']
        del request.session['email_change_new_email']
        del request.session['email_change_expiry']
        
        return JsonResponse({'success': True, 'message': 'Email updated successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def check_pending_email_change(request):
    """
    Check if there's a pending email change in the session.
    """
    session_otp = request.session.get('email_change_otp')
    session_email = request.session.get('email_change_new_email')
    session_expiry = request.session.get('email_change_expiry')
    
    has_pending = bool(session_otp and session_email and session_expiry)
    is_expired = False
    
    if has_pending and session_expiry:
        is_expired = time.time() > session_expiry
    
    # Return email only if not expired
    if has_pending and not is_expired:
        return JsonResponse({
            'has_pending': True,
            'email': session_email
        })
    else:
        return JsonResponse({
            'has_pending': False,
            'email': None
        })

class CustomLoginView(BaseLoginView):
    """Custom login view that checks email verification"""
    template_name = "accounts/login.html"
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Check if email is verified before allowing login"""
        # Email is already normalized to lowercase by CustomAuthenticationForm
        email = form.cleaned_data.get('username', '').strip()
        password = form.cleaned_data.get('password')
        
        # Authenticate user with normalized email
        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            # Check if email is verified
            if not user.is_email_verified:
                # Don't log them in, show error message
                form.add_error(None, 'Please verify your email address before logging in. Check your inbox for the verification email.')
                return self.form_invalid(form)
        
        # If email is verified, proceed with normal login
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle invalid form, including unverified email case"""
        # Check if user exists but email is not verified
        email = form.data.get('username', '').lower()
        password = form.data.get('password', '')
        
        try:
            user = CustomUser.objects.get(email=email)
            # Check if password is correct but email not verified
            if user.check_password(password) and not user.is_email_verified:
                # User exists and password is correct, but email not verified
                return render(self.request, self.template_name, {
                    'form': form,
                    'email_not_verified': True,
                    'user_email': email,
                })
        except CustomUser.DoesNotExist:
            pass
        
        return super().form_invalid(form)

class CustomPasswordResetConfirmView(BasePasswordResetConfirmView):
    """Custom password reset confirm view that shows better error messages"""
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Django's PasswordResetConfirmView sets 'validlink' to False if token is invalid/expired
        if not context.get('validlink', True):
            context['error_message'] = 'The password reset link is invalid or has expired. Password reset links can only be used once and expire after 24 hours.'
        return context

class CustomLogoutView(BaseLogoutView):
    """Custom logout view that handles both GET and POST requests"""
    next_page = reverse_lazy("accounts:login")
    
    def dispatch(self, request, *args, **kwargs):
        # Allow both GET and POST for logout
        # GET is convenient for users, POST is more secure
        if request.method == 'GET':
            # For GET requests, just log out without CSRF check
            # This is acceptable for logout as it's not a sensitive operation
            logout(request)
            messages.success(request, 'You have been logged out successfully.')
            return redirect(self.next_page)
        # For POST requests, use the parent's dispatch which handles CSRF
        return super().dispatch(request, *args, **kwargs)

@ensure_csrf_cookie
def resend_verification_email(request):
    """Resend verification email to user"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
            
            try:
                user = CustomUser.objects.get(email=email)
                
                # Only send if email is not already verified
                if user.is_email_verified:
                    return JsonResponse({'success': False, 'error': 'Email is already verified'}, status=400)
                
                # Send verification email
                try:
                    send_verification_email(request, user)
                    return JsonResponse({'success': True, 'message': 'Verification email sent successfully'})
                except Exception as email_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending verification email: {str(email_error)}")
                    return JsonResponse({'success': False, 'error': 'Failed to send verification email. Please try again later.'}, status=500)
            except CustomUser.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User with this email does not exist'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in resend_verification_email: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # For GET requests, return the CSRF token (useful for AJAX)
    if request.method == 'GET':
        return JsonResponse({'csrf_token': get_token(request)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@require_http_methods(["GET", "POST"])
def complete_invitation(request, token):
    """Complete registration for invited users
    
    The link can be clicked multiple times (GET requests) until:
    - The user completes registration (POST request)
    - The invitation expires (7 days)
    - The relationship is deleted
    """
    # Look up relationship by token - token should persist until POST (registration completion)
    try:
        relationship = MentorClientRelationship.objects.get(invitation_token=token)
    except MentorClientRelationship.DoesNotExist:
        messages.error(request, 'Invalid or expired invitation link. The link may have been used or the invitation may have been cancelled.')
        return redirect('accounts:login')
    except MentorClientRelationship.MultipleObjectsReturned:
        # This shouldn't happen due to unique constraint, but handle it gracefully
        relationship = MentorClientRelationship.objects.filter(invitation_token=token).first()
    
    # Check if invitation has expired (7 days from when it was sent)
    from datetime import timedelta
    expiration_time = relationship.invited_at + timedelta(days=7)
    if timezone.now() > expiration_time:
        messages.error(request, 'This invitation link has expired (valid for 7 days). Please ask the mentor to send a new invitation.')
        return redirect('accounts:login')
    
    # Check if already completed
    if relationship.confirmed and relationship.status == 'confirmed':
        messages.info(request, 'This invitation has already been completed. Please log in.')
        return redirect('accounts:login')
    
    user = relationship.client.user
    
    if request.method == 'POST':
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        errors = []
        
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not password1:
            errors.append('Password is required.')
        elif len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        elif password1 != password2:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update user profile
            user_profile = relationship.client
            user_profile.first_name = first_name
            user_profile.last_name = last_name
            user_profile.save()
            
            # Set password
            user.set_password(password1)
            user.is_email_verified = True  # Auto-verify email after registration completion
            user.save()
            
            # Update relationship - automatically confirm after registration
            relationship.confirmed = True
            relationship.status = 'confirmed'
            relationship.verified_at = timezone.now()
            relationship.invitation_token = None  # Clear token after use
            relationship.save()
            
            # Also add to the ManyToMany relationship if not already there
            if relationship.client not in relationship.mentor.clients.all():
                relationship.mentor.clients.add(relationship.client)
            
            messages.success(request, 'Registration completed successfully! Your email has been verified and you can now log in.')
            return redirect('accounts:login')
    
    return render(request, 'accounts/complete_invitation.html', {
        'relationship': relationship,
        'mentor_name': f"{relationship.mentor.first_name} {relationship.mentor.last_name}",
        'user_email': user.email,
    })


@require_http_methods(["GET", "POST"])
def confirm_mentor_invitation(request, token):
    """Confirm mentor invitation for existing users
    
    The link can be clicked multiple times (GET requests) until:
    - The user accepts it (POST request)
    - The invitation expires (7 days)
    - The relationship is deleted
    """
    # Look up relationship by token - token should persist until POST (acceptance)
    try:
        relationship = MentorClientRelationship.objects.get(confirmation_token=token)
    except MentorClientRelationship.DoesNotExist:
        messages.error(request, 'Invalid or expired confirmation link. The link may have been used or the invitation may have been cancelled.')
        return redirect('accounts:login')
    except MentorClientRelationship.MultipleObjectsReturned:
        # This shouldn't happen due to unique constraint, but handle it gracefully
        relationship = MentorClientRelationship.objects.filter(confirmation_token=token).first()
    
    # Check if invitation has expired (7 days from when it was sent)
    from datetime import timedelta
    expiration_time = relationship.invited_at + timedelta(days=7)
    if timezone.now() > expiration_time:
        messages.error(request, 'This invitation link has expired (valid for 7 days). Please ask the mentor to send a new invitation.')
        return redirect('accounts:login')
    
    # Check if already confirmed - if so, just redirect (token is still valid for viewing)
    if relationship.confirmed and relationship.status == 'confirmed':
        messages.info(request, 'This invitation has already been accepted.')
        if request.user.is_authenticated:
            return redirect('general:index')  # Will redirect to appropriate dashboard
        return redirect('accounts:login')
    
    # Check if status is inactive and not confirmed - this is the only valid status for accepting
    if relationship.status != 'inactive' or relationship.confirmed:
        messages.error(request, 'This invitation is no longer valid.')
        return redirect('accounts:login')
    
    # If user is not logged in, redirect to login with next parameter
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to accept this invitation.')
        from django.urls import reverse
        login_url = reverse('accounts:login') + f'?next={request.path}'
        return redirect(login_url)
    
    # Verify the user matches - if wrong user is logged in, log them out first
    if request.user != relationship.client.user:
        # Log out the current user (whoever is logged in)
        logout(request)
        messages.warning(request, f'This invitation is for {relationship.client.user.email}. Please log in with that account to accept the invitation.')
        from django.urls import reverse
        login_url = reverse('accounts:login') + f'?next={request.path}'
        return redirect(login_url)
    
    if request.method == 'POST':
        # Confirm the relationship - set confirmed and status to confirmed
        relationship.confirmed = True
        relationship.status = 'confirmed'
        relationship.verified_at = timezone.now()
        relationship.confirmation_token = None  # Clear token after use
        relationship.save(update_fields=['confirmed', 'status', 'verified_at', 'confirmation_token'])
        
        # Also add to the ManyToMany relationship if not already there
        if relationship.client not in relationship.mentor.clients.all():
            relationship.mentor.clients.add(relationship.client)
        
        messages.success(request, f'You have been successfully added as a client of {relationship.mentor.first_name} {relationship.mentor.last_name}.')
        # Redirect to user dashboard
        try:
            from django.urls import reverse
            return redirect(reverse('general:index'))  # Will redirect to appropriate dashboard
        except:
            return redirect('/dashboard/user/')
    
    return render(request, 'accounts/confirm_mentor_invitation.html', {
        'relationship': relationship,
        'mentor_name': f"{relationship.mentor.first_name} {relationship.mentor.last_name}",
    })


@login_required
@require_POST
def respond_to_invitation(request, relationship_id):
    """Accept or deny a mentor invitation"""
    if not hasattr(request.user, 'user_profile'):
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=400)
    
    if not request.user.is_email_verified:
        return JsonResponse({'success': False, 'error': 'Please verify your email first'}, status=400)
    
    user_profile = request.user.user_profile
    
    try:
        relationship = MentorClientRelationship.objects.get(
            id=relationship_id,
            client=user_profile,
            confirmed=False,
            status='inactive'
        )
    except MentorClientRelationship.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invitation not found or already processed'}, status=404)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'accept' or 'deny'
        
        if action == 'accept':
            # Confirm the relationship
            relationship.confirmed = True
            relationship.status = 'confirmed'
            relationship.verified_at = timezone.now()
            relationship.confirmation_token = None  # Clear token after use
            relationship.save(update_fields=['confirmed', 'status', 'verified_at', 'confirmation_token'])
            
            # Also add to the ManyToMany relationship if not already there
            if relationship.client not in relationship.mentor.clients.all():
                relationship.mentor.clients.add(relationship.client)
            
            return JsonResponse({
                'success': True,
                'message': f'You have been successfully added as a client of {relationship.mentor.first_name} {relationship.mentor.last_name}.'
            })
        
        elif action == 'deny':
            # Set status to denied, confirmed stays False
            relationship.status = 'denied'
            relationship.confirmation_token = None  # Clear token
            relationship.save(update_fields=['status', 'confirmation_token'])
            
            return JsonResponse({
                'success': True,
                'message': f'You have declined the invitation from {relationship.mentor.first_name} {relationship.mentor.last_name}.'
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action. Use "accept" or "deny".'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
