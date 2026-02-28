from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.filter
def get_nested(dictionary, keys):
    """
    Get nested item from dictionary using dot-separated keys.
    Example: existing_items|get_nested:"product_id.packs"
    """
    if dictionary is None:
        return 0
    
    # Split keys if string, otherwise assume it's already a list
    if isinstance(keys, str):
        key_list = keys.split('.')
    else:
        key_list = [keys]
    
    result = dictionary
    for key in key_list:
        if result is None:
            return 0
        # Try to convert to int if it looks like a number
        try:
            key = int(key)
        except (ValueError, TypeError):
            pass
        result = result.get(key, None) if isinstance(result, dict) else None
    
    return result if result is not None else 0
