import re
from django.template.defaultfilters import slugify

#Snippet 690 - modified
def unique_strvalue(instance, value, field_name='slug', queryset=None,
                   separator='-', slug=False):
    """
    Calculates and stores a unique string of ``value`` for an instance.

    ``field_name`` should be a string matching the name of the field to
    store the string in (and the field to check against for uniqueness).

    ``queryset`` usually doesn't need to be explicitly provided - it'll default
    to using the ``.all()`` queryset from the model's default manager.
    """
    field = instance._meta.get_field(field_name)

    strfield = getattr(instance, field.attname)
    field_len = field.max_length

    # Sort out the initial slug, limiting its length if necessary.
    if slug:
        strval = slugify(value)
    else:
        strval = value
    if field_len:
        strval = strval[:field_len]
    if slug:
        strval = _str_strip(strval, separator)
    original_strval = strval

    # Create the queryset if one wasn't explicitly provided and exclude the
    # current instance from the queryset.
    if queryset is None:
        queryset = instance.__class__._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    # Find a unique string. If one matches, at '-2' to the end and try again
    # (then '-3', etc).
    next = 2
    while not strval or queryset.filter(**{field_name: strval}):
        strval = original_strval
        end = '%s%s' % (separator, next)
        if field_len and len(strval) + len(end) > field_len:
            strval = slug[:field_len-len(end)]
            if slug:
                strval = _str_strip(strval, separator)
        strval = '%s%s' % (strval, end)
        next += 1

    setattr(instance, field.attname, strval)


def _str_strip(value, separator='-'):
    """
    Cleans up a strig by removing separator characters that occur at the
    beginning or end of a string.

    If an alternate separator is used, it will also replace any instances of
    the default '-' separator with the new separator.
    """
    separator = separator or ''
    if separator == '-' or not separator:
        re_sep = '-'
    else:
        re_sep = '(?:-|%s)' % re.escape(separator)
    # Remove multiple instances and if an alternate separator is provided,
    # replace the default '-' separator.
    if separator != re_sep:
        value = re.sub('%s+' % re_sep, separator, value)
    # Remove separator from the beginning and end of the slug.
    if separator:
        if separator != '-':
            re_sep = re.escape(separator)
        value = re.sub(r'^%s+|%s+$' % (re_sep, re_sep), '', value)
    return value
