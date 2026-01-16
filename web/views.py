from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Min, Max
from django.db.models.functions import Coalesce
from django.db import models
from django.core.paginator import Paginator
from accounts.models import CustomUser, MentorProfile
from general.models import BlogPost
from dashboard_mentor.constants import PREDEFINED_CATEGORIES, PREDEFINED_LANGUAGES, QUALIFICATION_TYPES
import json

def landing(request):
    # Pass predefined data for filters (same as mentors page)
    from dashboard_mentor.constants import PREDEFINED_CATEGORIES, PREDEFINED_LANGUAGES
    
    # Get min and max prices for slider
    all_mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True, collisions=False)
    price_stats = all_mentors.aggregate(
        min_price=Min('price_per_hour'),
        max_price=Max('price_per_hour')
    )
    min_price = 0  # Always allow slider to go from 0
    max_price = int(price_stats['max_price'] or 200)
    if max_price < 200:
        max_price = 200
    
    context = {
        'predefined_categories': PREDEFINED_CATEGORIES,
        'predefined_languages': PREDEFINED_LANGUAGES,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, "web/landing.html", context)

def mentors(request):
    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    language_id = request.GET.get('language', '').strip()
    max_price = request.GET.get('price', '').strip()
    first_session_free = request.GET.get('first_session_free', '').strip() == 'true'
    page = int(request.GET.get('page', 1))
    per_page = 12  # Number of mentors per page
    
    # Start with all active mentor profiles
    mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True, collisions=False)
    
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
            # If max_price is 200 (the slider max), treat it as "200+" (no upper limit)
            # Otherwise, filter by price_per_hour <= max_price
            if max_price_decimal < 200:
                mentors = mentors.filter(price_per_hour__lte=max_price_decimal)
            # If max_price is 200, don't filter by price (show all prices)
        except ValueError:
            pass
    
    # Filter by first session free
    if first_session_free:
        mentors = mentors.filter(first_session_free=True)
    
    
    # Order by name
    mentors = mentors.order_by('first_name', 'last_name')
    
    # Get total count before pagination
    total_count = mentors.count()
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    mentors_page = mentors[start:end]
    
    # Get min and max prices for slider (from all active mentors, not just filtered)
    all_mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True, collisions=False)
    price_stats = all_mentors.aggregate(
        min_price=Min('price_per_hour'),
        max_price=Max('price_per_hour')
    )
    
    # Default to 0-200 if no prices found
    # Always allow slider to go from 0, regardless of actual min price in DB
    min_price = 0
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
        ).filter(user__is_active=True, user__is_email_verified=True, collisions=False)[:10]
    else:
        # Single word - search in both first and last name
        mentors = MentorProfile.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(user__email__icontains=query)
        ).filter(user__is_active=True, user__is_email_verified=True, collisions=False)[:10]
    
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
    page = int(request.GET.get('page', 1))
    per_page = 12
    
    # Start with all active mentor profiles
    mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True, collisions=False)
    
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
            # If max_price is 200 (the slider max), treat it as "200+" (no upper limit)
            # Otherwise, filter by price_per_hour <= max_price
            if max_price_decimal < 200:
                mentors = mentors.filter(price_per_hour__lte=max_price_decimal)
            # If max_price is 200, don't filter by price (show all prices)
        except ValueError:
            pass
    
    if first_session_free:
        mentors = mentors.filter(first_session_free=True)
    
    
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

def landing_mentors_load(request):
    """API endpoint for loading mentors on landing page with filters"""
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    language_id = request.GET.get('language', '').strip()
    max_price = request.GET.get('price', '').strip()
    first_session_free = request.GET.get('first_session_free', '').strip() == 'true'
    
    # Start with all active mentor profiles
    mentors = MentorProfile.objects.filter(user__is_active=True, user__is_email_verified=True)
    
    # Apply filters (same logic as mentors view)
    if search_query:
        query_words = search_query.strip().split()
        if len(query_words) >= 2:
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
            if max_price_decimal < 200:
                mentors = mentors.filter(price_per_hour__lte=max_price_decimal)
        except ValueError:
            pass
    
    if first_session_free:
        mentors = mentors.filter(first_session_free=True)
    
    mentors = mentors.order_by('first_name', 'last_name')[:12]  # Limit to 12 for landing page
    
    mentor_data = []
    for mentor in mentors:
        avatar_url = None
        if mentor.profile_picture:
            try:
                avatar_url = mentor.profile_picture.url
            except:
                pass
        
        mentor_data.append({
            'id': mentor.user.id,
            'first_name': mentor.first_name,
            'last_name': mentor.last_name,
            'mentor_type': mentor.mentor_type or 'Mentor',
            'profile_picture': avatar_url,
            'quote': mentor.quote,
            'bio': mentor.bio,
            'tags': mentor.tags or [],
            'price_per_hour': float(mentor.price_per_hour) if mentor.price_per_hour else None,
        })
    
    return JsonResponse({
        'mentors': mentor_data,
        'count': len(mentor_data),
    })

def mentor_profile_detail(request, user_id):
    mentor_user = get_object_or_404(CustomUser, id=user_id)
    try:
        mentor_profile = mentor_user.mentor_profile
    except:
        return render(request, "web/mentor_profile_detail.html", {"error": "Mentor profile not found"})
    
    # Check if logged-in user has already had a session with this mentor
    is_first_session = True
    if request.user.is_authenticated:
        try:
            from accounts.models import MentorClientRelationship
            user_profile = request.user.user_profile
            relationship = MentorClientRelationship.objects.filter(
                mentor=mentor_profile,
                client=user_profile
            ).first()
            
            # It's first session if no relationship exists or first_session_scheduled is False
            is_first_session = relationship is None or not relationship.first_session_scheduled
        except Exception:
            # If any error, assume it's first session
            is_first_session = True
    
    return render(request, "web/mentor_profile_detail.html", {
        "mentor_user": mentor_user,
        "mentor_profile": mentor_profile,
        "predefined_languages": PREDEFINED_LANGUAGES,
        "qualification_types": QUALIFICATION_TYPES,
        "is_first_session": is_first_session,
    })


def blog_list(request):
    """Public blog list page with filtering by mentor and category"""
    # Only show published posts
    posts = BlogPost.objects.filter(status='published').order_by('-published_at', '-created_at')
    
    # Filter by mentor (from query parameter)
    mentor_id = request.GET.get('mentor')
    mentor_filter = None
    if mentor_id:
        try:
            mentor_user = CustomUser.objects.get(id=int(mentor_id))
            if hasattr(mentor_user, 'mentor_profile'):
                posts = posts.filter(author=mentor_user)
                mentor_filter = mentor_user.mentor_profile
        except (ValueError, CustomUser.DoesNotExist):
            pass
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        # Filter posts where categories JSONField contains the category ID
        posts = posts.filter(categories__contains=[category_filter])
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(posts, 12)  # 12 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get list of mentors who have published posts (for filter dropdown)
    mentors_with_posts = CustomUser.objects.filter(
        blog_posts__status='published'
    ).distinct().select_related('mentor_profile')
    
    return render(request, "web/blog_list.html", {
        "page_obj": page_obj,
        "posts": page_obj,
        "predefined_categories": PREDEFINED_CATEGORIES,
        "mentors_with_posts": mentors_with_posts,
        "mentor_filter": mentor_filter,
        "category_filter": category_filter,
        "search_query": search_query,
    })


def blog_detail(request, slug):
    """Public blog post detail page with SEO meta tags"""
    post = get_object_or_404(BlogPost, slug=slug, status='published')
    
    # Get related posts (same categories, excluding current post)
    related_posts = BlogPost.objects.filter(
        status='published',
        categories__overlap=post.categories
    ).exclude(id=post.id).distinct()[:3]
    
    # If not enough related posts, get recent posts
    if related_posts.count() < 3:
        recent_posts = BlogPost.objects.filter(
            status='published'
        ).exclude(id=post.id).order_by('-published_at')[:3]
        related_posts = list(related_posts) + list(recent_posts[:3 - related_posts.count()])
    
    # Build absolute URL for cover image (for SEO)
    cover_image_url = None
    if post.cover_image:
        # Use request.build_absolute_uri to get the full URL
        cover_image_url = request.build_absolute_uri(post.cover_image.url)
    
    # Get author info
    author_name = post.author_name
    author_is_mentor = post.author_is_mentor
    author_user_id = post.author.id if author_is_mentor else None
    author_mentor_profile = None
    
    # Get mentor profile if author is a mentor
    if author_is_mentor and author_user_id:
        try:
            author_user = CustomUser.objects.get(id=author_user_id)
            if hasattr(author_user, 'mentor_profile'):
                author_mentor_profile = author_user.mentor_profile
        except CustomUser.DoesNotExist:
            pass
    
    # Get other articles by the same author
    author_other_posts = BlogPost.objects.filter(
        author=post.author,
        status='published'
    ).exclude(id=post.id).order_by('-published_at')[:5]
    
    return render(request, "web/blog_detail.html", {
        "post": post,
        "related_posts": related_posts,
        "cover_image_url": cover_image_url,
        "author_name": author_name,
        "author_is_mentor": author_is_mentor,
        "author_user_id": author_user_id,
        "author_mentor_profile": author_mentor_profile,
        "author_other_posts": author_other_posts,
        "predefined_categories": PREDEFINED_CATEGORIES,
    })
