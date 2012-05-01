from django.core.urlresolvers import reverse
from django import template
from django.utils.dateformat import format

from photologue.models import Photo, Video, VideoSize
from photologue.utils.snippets import format_date_range

register = template.Library()

@register.simple_tag
def model_url(urlname, model_type, *args, **kwargs):
    return reverse(urlname.replace('TYPE', model_type), args=args)

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

@register.simple_tag
def video_sources(video, size_pattern):
    sources = ""
    sizes = VideoSize.objects.filter(name__contains=size_pattern)
    for size in sizes:
        url_func = 'get_%s_url' % size.name
        if hasattr(video, url_func):
            url = getattr(video, url_func)()
            if url:
                sources += "<source src=\"" + url + "\" type='" + size.source_type() + "' />\n"
    return sources

@register.simple_tag
def video_downloads(video, size_pattern):
    sources = "<a href=\"" + video.file.url + "\">original</a>\n"
    sizes = VideoSize.objects.filter(name__contains=size_pattern)
    for size in sizes:
        url_func = 'get_%s_url' % size.name
        if hasattr(video, url_func):
            url = getattr(video, url_func)()
            if url:
                sources += "<a href=\"" + url + "\">" + size.videotype + "</a>\n"
    return sources


from photologue.models import Race

@register.simple_tag
def race_event(video):
    try:
        race = Race.objects.get(video=video)
    except Race.DoesNotExist:
        return ""
    event = race.event
    if not event:
        return ""
    out = format_date_range(event.day_start, event.day_end)
    out += " - " + event.title
    out += " - " + format(race.video.date_taken, "l")
    return out
