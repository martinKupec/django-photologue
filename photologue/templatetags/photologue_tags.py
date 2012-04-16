from django.core.urlresolvers import reverse
from django import template

from photologue.models import Photo, Video

register = template.Library()

@register.simple_tag
def media_url(urlname, media_type, num, *args, **kwargs):
	return reverse(urlname.replace('TYPE', media_type), args=[num])

@register.inclusion_tag('photologue/tags/gallery_list.html')
def list_galleries(galleries, sample_size=None):
    """ Return a list of galleries """
    return {'object_list': galleries, 'sample_size': sample_size}

@register.inclusion_tag('photologue/tags/gallery_item.html')
def gallery_item(item):
    """ Return a specified item """
    return {'item': item}

@register.inclusion_tag('photologue/tags/gallery_items.html')
def gallery_items(items, restrict=None):
    """ Return a specified items """
    if restrict:
        return {'object_list': items[:restrict]}
    else:
        return {'object_list': items}

@register.inclusion_tag('photologue/tags/next_in_gallery.html')
def next_in_gallery(photo, gallery):
    return {'photo': photo.get_next_in_gallery(gallery)}

@register.inclusion_tag('photologue/tags/prev_in_gallery.html')
def previous_in_gallery(photo, gallery):
    return {'photo': photo.get_previous_in_gallery(gallery)}

@register.inclusion_tag('photologue/tags/gallery_photo.html')
def random_photos(number=0, is_public=True):
    """
    Return a specified number of random photos from all galleries
    """
    return {'object_list': Photo.objects.sample(number, is_public)}
