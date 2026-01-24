from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key (handles both string and integer keys)"""
    if dictionary is None:
        return None
    # Try the key as-is first
    if key in dictionary:
        return dictionary.get(key, '')
    # If not found, try as string (answers are stored with string keys)
    if str(key) in dictionary:
        return dictionary.get(str(key), '')
    # If still not found, try as integer (in case dictionary has integer keys)
    try:
        int_key = int(key)
        if int_key in dictionary:
            return dictionary.get(int_key, '')
    except (ValueError, TypeError):
        pass
    return ''
