from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Min, Max
from django.db.models.functions import Coalesce
from django.db import models
from accounts.models import CustomUser, MentorProfile
from dashboard_mentor.constants import PREDEFINED_CATEGORIES, PREDEFINED_LANGUAGES, COMMON_TIMEZONES
import json

def landing(request):
    return render(request, "web/landing.html")

def mentors(request):
    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    language_id = request.GET.get('language', '').strip()
    max_price = request.GET.get('price', '').strip()
    first_session_free = request.GET.get('first_session_free', '').strip() == 'true'
    timezone_min = request.GET.get('timezone_min', '').strip()
    timezone_max = request.GET.get('timezone_max', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = 12  # Number of mentors per page
    
    # Start with all active mentor profiles
    mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True)
    
    # Filter by search query (name)
    if search_query:
        # Split search query into words to search both first and last name
        query_words = search_query.strip().split()
        if len(query_words) >= 2:
            # If multiple words, try to match first word with first_name and second word with last_name
            # Also try reverse order and individual word matches
            first_word = query_words[0]
            last_word = query_words[-1]
            mentors = mentors.filter(
                (Q(first_name__icontains=first_word) & Q(last_name__icontains=last_word)) |
                (Q(first_name__icontains=last_word) & Q(last_name__icontains=first_word)) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        else:
            # Single word - search in both first and last name
            mentors = mentors.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
    
    # Filter by category (SQLite-compatible JSONField filtering)
    if category_id:
        # For SQLite, use icontains on JSON string representation
        mentors = mentors.filter(categories__icontains=category_id)
    
    # Filter by language (SQLite-compatible JSONField filtering)
    if language_id:
        # For SQLite, use icontains on JSON string representation
        mentors = mentors.filter(languages__icontains=language_id)
    
    # Filter by price
    if max_price:
        try:
            max_price_decimal = float(max_price)
            # Only show mentors with price_per_hour <= max_price (exclude null prices)
            mentors = mentors.filter(price_per_hour__lte=max_price_decimal)
        except ValueError:
            pass
    
    # Filter by first session free
    if first_session_free:
        mentors = mentors.filter(first_session_free=True)
    
    # Filter by timezone range (if both min and max are provided)
    if timezone_min and timezone_max:
        # Get timezone offsets for filtering
        min_tz = next((tz for tz in COMMON_TIMEZONES if tz['id'] == timezone_min), None)
        max_tz = next((tz for tz in COMMON_TIMEZONES if tz['id'] == timezone_max), None)
        if min_tz and max_tz:
            # Filter mentors whose selected_timezone is in the range
            # This is a simplified approach - you might want to parse UTC offsets for more accurate filtering
            mentors = mentors.filter(
                selected_timezone__isnull=False
            )
    
    # Order by name
    mentors = mentors.order_by('first_name', 'last_name')
    
    # Get total count before pagination
    total_count = mentors.count()
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    mentors_page = mentors[start:end]
    
    # Get min and max prices for slider (from all active mentors, not just filtered)
    all_mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True)
    price_stats = all_mentors.aggregate(
        min_price=Min('price_per_hour'),
        max_price=Max('price_per_hour')
    )
    
    # Default to 0-200 if no prices found
    min_price = int(price_stats['min_price'] or 0)
    max_price = int(price_stats['max_price'] or 200)
    
    # Ensure max is at least 200 for better UX
    if max_price < 200:
        max_price = 200
    
    # Check if there are more pages
    has_next = end < total_count
    
    context = {
        'mentors': mentors_page,
        'predefined_categories': PREDEFINED_CATEGORIES,
        'predefined_languages': PREDEFINED_LANGUAGES,
        'common_timezones': COMMON_TIMEZONES,
        'min_price': min_price,
        'max_price': max_price,
        'current_page': page,
        'has_next': has_next,
        'total_count': total_count,
        'current_filters': {
            'q': search_query,
            'category': category_id,
            'language': language_id,
            'price': max_price if not max_price else (int(max_price) if max_price else max_price),
            'first_session_free': first_session_free,
            'timezone_min': timezone_min,
            'timezone_max': timezone_max,
        }
    }
    
    return render(request, "web/mentors.html", context)

def mentor_search_suggestions(request):
    """API endpoint for mentor name search suggestions"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Search mentors by name - handle full names better
    query_words = query.strip().split()
    if len(query_words) >= 2:
        # If multiple words, try to match first word with first_name and second word with last_name
        # Also try reverse order and individual word matches
        first_word = query_words[0]
        last_word = query_words[-1]
        mentors = MentorProfile.objects.filter(
            (Q(first_name__icontains=first_word) & Q(last_name__icontains=last_word)) |
            (Q(first_name__icontains=last_word) & Q(last_name__icontains=first_word)) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(user__email__icontains=query)
        ).filter(user__is_active=True, user__is_email_verified=True)[:10]
    else:
        # Single word - search in both first and last name
        mentors = MentorProfile.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(user__email__icontains=query)
        ).filter(user__is_active=True, user__is_email_verified=True)[:10]
    
    suggestions = []
    for mentor in mentors:
        avatar_url = None
        if mentor.profile_picture:
            try:
                avatar_url = mentor.profile_picture.url
            except:
                pass
        
        suggestions.append({
            'id': mentor.user.id,
            'name': f"{mentor.first_name} {mentor.last_name}",
            'mentor_type': mentor.mentor_type or 'Mentor',
            'avatar_url': avatar_url,
        })
    
    return JsonResponse({'suggestions': suggestions})

def mentors_load_more(request):
    """API endpoint for loading more mentors (infinite scroll)"""
    # Get filter parameters (same as mentors view)
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    language_id = request.GET.get('language', '').strip()
    max_price = request.GET.get('price', '').strip()
    first_session_free = request.GET.get('first_session_free', '').strip() == 'true'
    timezone_min = request.GET.get('timezone_min', '').strip()
    timezone_max = request.GET.get('timezone_max', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = 12
    
    # Start with all active mentor profiles
    mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True)
    
    # Apply same filters as mentors view
    if search_query:
        # Split search query into words to search both first and last name
        query_words = search_query.strip().split()
        if len(query_words) >= 2:
            # If multiple words, try to match first word with first_name and second word with last_name
            # Also try reverse order and individual word matches
            first_word = query_words[0]
            last_word = query_words[-1]
            mentors = mentors.filter(
                (Q(first_name__icontains=first_word) & Q(last_name__icontains=last_word)) |
                (Q(first_name__icontains=last_word) & Q(last_name__icontains=first_word)) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        else:
            # Single word - search in both first and last name
            mentors = mentors.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
    
    if category_id:
        mentors = mentors.filter(categories__icontains=category_id)
    
    if language_id:
        mentors = mentors.filter(languages__icontains=language_id)
    
    if max_price:
        try:
            max_price_decimal = float(max_price)
            mentors = mentors.filter(price_per_hour__lte=max_price_decimal)
        except ValueError:
            pass
    
    if first_session_free:
        mentors = mentors.filter(first_session_free=True)
    
    if timezone_min and timezone_max:
        mentors = mentors.filter(selected_timezone__isnull=False)
    
    # Order by name
    mentors = mentors.order_by('first_name', 'last_name')
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    mentors_page = mentors[start:end]
    
    # Check if there are more pages
    total_count = mentors.count()
    has_next = end < total_count
    
    # Serialize mentors
    mentors_data = []
    for mentor in mentors_page:
        avatar_url = None
        if mentor.profile_picture:
            try:
                avatar_url = mentor.profile_picture.url
            except:
                pass
        
        mentors_data.append({
            'id': mentor.user.id,
            'first_name': mentor.first_name,
            'last_name': mentor.last_name,
            'mentor_type': mentor.mentor_type or 'Mentor',
            'quote': mentor.quote or '',
            'bio': mentor.bio or '',
            'tags': mentor.tags or [],
            'price_per_hour': float(mentor.price_per_hour) if mentor.price_per_hour else None,
            'avatar_url': avatar_url,
        })
    
    return JsonResponse({
        'mentors': mentors_data,
        'has_next': has_next,
        'page': page,
        'total_count': total_count
    })

def terms(request):
    return render(request, "web/terms.html")

def privacy(request):
    return render(request, "web/privacy.html")

def mentor_profile_detail(request, user_id):
    mentor_user = get_object_or_404(CustomUser, id=user_id)
    try:
        mentor_profile = mentor_user.mentor_profile
    except:
        return render(request, "web/mentor_profile_detail.html", {"error": "Mentor profile not found"})
    
    return render(request, "web/mentor_profile_detail.html", {
        "mentor_user": mentor_user,
        "mentor_profile": mentor_profile,
    })
