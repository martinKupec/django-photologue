from django.conf import settings
from django.conf.urls.defaults import *
from models import *

# Number of random images from the gallery to display.
SAMPLE_SIZE = getattr(settings, 'GALLERY_SAMPLE_SIZE', 5)

def add_view(view, dictionary):
    d = dictionary.copy()
    d['view'] = view
    return d

# galleries
gallery_args = {'date_field': 'date_added', 'allow_empty': True, 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}
urlpatterns = patterns('django.views.generic.date_based',
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'date_field': 'date_added', 'slug_field': 'title_slug', 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery-detail'),
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'archive_day', gallery_args, name='pl-gallery-archive-day'),
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'archive_month', gallery_args, name='pl-gallery-archive-month'),
    url(r'^gallery/(?P<year>\d{4})/$', 'archive_year', gallery_args, name='pl-gallery-archive-year'),
    url(r'^gallery/?$', 'archive_index', gallery_args, name='pl-gallery-archive'),
)
urlpatterns += patterns('django.views.generic.list_detail',
    url(r'^gallery/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'slug_field': 'title_slug', 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery'),
    url(r'^gallery/page/(?P<page>[0-9]+)/$', 'object_list', {'queryset': Gallery.objects.filter(is_public=True), 'allow_empty': True, 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery-list'),
)

# photographs
photo_args = {'date_field': 'date_added', 'allow_empty': True, 'queryset': Photo.objects.filter(is_public=True)}

urlpatterns += patterns('django.views.generic.date_based',
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'date_field': 'date_added', 'slug_field': 'title_slug', 'queryset': Photo.objects.filter(is_public=True)}, name='pl-photo-detail'),
)

prefix='django.views.generic.date_based.'
urlpatterns += patterns('photologue.views',
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'media_meta', add_view(prefix+'archive_day', photo_args), name='pl-photo-archive-day'),
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'media_meta', add_view(prefix+'archive_month', photo_args), name='pl-photo-archive-month'),
    url(r'^photo/(?P<year>\d{4})/$', 'media_meta', add_view(prefix+'archive_year', photo_args), name='pl-photo-archive-year'),
)
prefix='django.views.generic.list_detail.'
urlpatterns += patterns('photologue.views',
    url(r'^photo/$', 'photo_index', name='pl-photo-archive'),
    url(r'^photo/page/(?P<page>[0-9]+)/$', 'media_meta', {'view': prefix+'object_list', 'queryset': Photo.objects.filter(is_public=True), 'allow_empty': True}, name='pl-photo-list'),
)
urlpatterns += patterns('django.views.generic.list_detail',
    url(r'^photo/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'slug_field': 'title_slug', 'queryset': Photo.objects.filter(is_public=True)}, name='pl-photo'),
)

# videos
video_args = {'date_field': 'date_added', 'allow_empty': True, 'queryset': Video.objects.filter(is_public=True)}

urlpatterns += patterns('django.views.generic.date_based',
    url(r'^video/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'date_field': 'date_added', 'slug_field': 'title_slug', 'queryset': Video.objects.filter(is_public=True)}, name='pl-video-detail'),
)
prefix='django.views.generic.date_based.'
urlpatterns += patterns('photologue.views',
    url(r'^video/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'media_meta', add_view(prefix+'archive_day', video_args), name='pl-video-archive-day'),
    url(r'^video/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'media_meta', add_view(prefix+'archive_month', video_args), name='pl-video-archive-month'),
    url(r'^video/(?P<year>\d{4})/$', 'media_meta', add_view(prefix+'archive_year', video_args), name='pl-video-archive-year'),
)
prefix='django.views.generic.list_detail.'
urlpatterns += patterns('photologue.views',
    url(r'^video/$', 'video_index', name='pl-video-archive'),
    url(r'^video/page/(?P<page>[0-9]+)/$', 'media_meta', {'view': prefix+'object_list', 'queryset': Video.objects.filter(is_public=True), 'allow_empty': True}, name='pl-video-list'),
)
urlpatterns += patterns('django.views.generic.list_detail',
    url(r'^video/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'slug_field': 'title_slug', 'queryset': Video.objects.filter(is_public=True)}, name='pl-video'),
)
