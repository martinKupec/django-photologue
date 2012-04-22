from django import forms
from django.http import HttpResponse
from django.utils import simplejson as json
from django.core.exceptions import ViewDoesNotExist
from django.views.generic.date_based import archive_index

from forms import AjaxRequestForm
from models import Photo

def media_meta(request, view, **kwargs):
    if callable(view):
        view_str = view.__name__
    else:
        view_str = get_mod_func(view)[1]
        try:
            view = get_callable(view)
        except ImportError, e:
            mod_name, _ = get_mod_func(view)
            raise ViewDoesNotExist("Could not import %s. Error was: %s" % (mod_name, str(e)))
        except AttributeError, e:
            mod_name, func_name = get_mod_func(view)
            raise ViewDoesNotExist("Tried %s in module %s. Error was: %s" % (func_name, mod_name, str(e)))

    model = kwargs['queryset'].model
    extra_context = {
        'media_type': model._meta.object_name.lower(),
        'media_name': model._meta.verbose_name.capitalize(),
        'media_name_plural': model._meta.verbose_name_plural.capitalize(),
    }
    if 'extra_context' in kwargs:
        kwargs['extra_context'].update(extra_context)
    else:
        kwargs['extra_context'] = extra_context
    kwargs['template_name'] = 'photologue/'+view_translate[view_str]
    return view(request, **kwargs)

def ajax_view(request):
    """
    Handle any async JS server function request
    """
    def JsonResponse(data):
        """
        Wraper to allow an easy method to return json data
        """
        return HttpResponse(json.dumps(data), mimetype='application/json')

    ajax_request = AjaxRequestForm(data=request.GET)
    if ajax_request.is_valid():
        request_type = ajax_request.cleaned_data['type']

        # sample()
        if request_type == 'sample':
            # Excluded is_public for obvious security reasons
            ajax_request.fields['count'] = forms.IntegerField(min_value=0, required=False)
            ajax_request.full_clean()
            if ajax_request.is_valid():
                photo_list = []
                photos = Photo.objects.sample(ajax_request.cleaned_data['count'])
                for photo in photos:
                    photo_list.append({
                        'thumbnail': photo.get_thumbnail_url(),
                        'title': photo.title,
                        'url': photo.get_absolute_url()
                    })
                return JsonResponse(photo_list)

def ajax_archive_index(request, **kwargs):
    if request.is_ajax():
        return ajax_view(request)
    return archive_index(request, **kwargs)
