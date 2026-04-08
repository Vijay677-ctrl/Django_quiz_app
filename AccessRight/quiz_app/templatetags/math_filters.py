from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divides the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
@register.filter
def get_option_text(question, option_num):
    """Retrieves option text based on the number (1-4)."""
    # Convert option_num to string to be safe
    num = str(option_num)
    if num == '1': return question.option_1
    if num == '2': return question.option_2
    if num == '3': return question.option_3
    if num == '4': return question.option_4
    return ""