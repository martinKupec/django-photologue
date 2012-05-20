from django.conf import settings
from django.conf.urls.defaults import *
from views import ajax_archive_index
from models import *

# Number of random images from the gallery to display.
SAMPLE_SIZE = ":%d" % getattr(settings, 'GALLERY_SAMPLE_SIZE', 5)

template_table = {
    'object_detail': u'%s_detail.html',
    'object_list': u'%s_list.html',
    'ajax_archive_index': u'%s_archive.html',
    'archive_index': u'%s_archive.html',
    'archive_year': u'%s_archive_year.html',
    'archive_month': u'%s_archive_month.html',
    'archive_day': u'%s_archive_day.html',
}

def meta_url(url, view, kwargs, name, type, type_args):
    if callable(view):
        view_str = view.__name__
    else:
        view_str = view
    new_kwargs = kwargs.copy()
    new_kwargs.update(type_args)
    model = new_kwargs['queryset'].model
    extra_context = {
        'model_type': model._meta.object_name.lower(),
        'model_name': model._meta.verbose_name,
        'model_name_plural': model._meta.verbose_name_plural,
    }
    if 'extra_context' in new_kwargs:
        new_kwargs['extra_context'].update(extra_context)
    else:
        new_kwargs['extra_context'] = extra_context
    new_kwargs['template_name'] = u'photologue/' + template_table[view_str] % type
    return (url, view, new_kwargs, name)

def gen_patterns(prefix, date_field, slug_field, model, template, common_detail):
    def gen_url(url, view, kwargs, name):
        return meta_url(url, view, kwargs, name, template, gen_args)

    model_name = model.__name__.lower()

    gen_args = {'date_field': date_field, 'queryset': model.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}
    urlpatterns = patterns('django.views.generic.date_based',
        gen_url(r'^' + prefix + '/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$',
            'object_detail', {'slug_field': slug_field}, 'pl-%s-detail' % model_name),
        gen_url(r'^' + prefix + '/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$',
            'archive_day', {'allow_empty': True}, 'pl-%s-archive-day' % model_name),
        gen_url(r'^' + prefix + '/(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
            'archive_month', {'allow_empty': True}, 'pl-%s-archive-month' % model_name),
        gen_url(r'^' + prefix + '/(?P<year>\d{4})/$',
            'archive_year', {'allow_empty': True}, 'pl-%s-archive-year' % model_name),
        gen_url(r'^' + prefix + '/?$',
            ajax_archive_index, {'allow_empty': True}, 'pl-%s-archive' % model_name),
    )
    
    gen_args = {'queryset': model.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}
    urlpatterns += patterns('django.views.generic.list_detail',
        gen_url(r'^' + prefix + '/(?P<slug>[\-\d\w]+)/$',
            'object_detail', {'slug_field': slug_field}, 'pl-%s' % model_name) if common_detail else
                url(r'^' + prefix + '/(?P<slug>[\-\d\w]+)/$',
            'object_detail', {'slug_field': slug_field, 'queryset': model.objects.filter(is_public=True)}, 'pl-%s' % model_name),
        gen_url(r'^' + prefix + '/page/(?P<page>[0-9]+)/$', 'object_list', {'allow_empty': True}, 'pl-%s-list' % model_name),
    )
    return urlpatterns

urlpatterns = gen_patterns('gallery', 'date_added', 'title_slug', Gallery, u'gallery', True)
urlpatterns += gen_patterns('photo', 'date_added', 'title_slug', Photo, u'media', False)
urlpatterns += gen_patterns('video', 'date_added', 'title_slug', Video, u'media', False)
