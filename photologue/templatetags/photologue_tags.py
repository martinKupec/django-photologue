from django.core.urlresolvers import reverse
from django import template

from photologue.models import Photo, Video

register = template.Library()

@register.simple_tag
def media_url(urlname, media_type, *args, **kwargs):
    return reverse(urlname.replace('TYPE', media_type), args=args)

@register.inclusion_tag('photologue/gallery_item.html')
def next_in_gallery(item, gallery):
    return {'item': item.get_next_in_gallery(gallery), 'nodiv': True}

@register.inclusion_tag('photologue/gallery_item.html')
def previous_in_gallery(item, gallery):
    return {'item': item.get_previous_in_gallery(gallery), 'nodiv': True}

@register.inclusion_tag('photologue/tags/gallery_photo.html')
def random_photos(number=0, is_public=True):
    """
    Return a specified number of random photos from all galleries
    """
    return {'object_list': Photo.objects.sample(number, is_public)}
