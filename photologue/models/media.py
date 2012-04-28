from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import curry
from django.utils.timezone import now
from django.utils.encoding import smart_str, force_unicode

from photologue.default_settings import *

class MediaModel(models.Model):
    file = models.FileField(_('file'), max_length=MEDIA_FIELD_MAX_LENGTH,
                              upload_to=get_storage_path, blank=False)
    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    crop_from = models.CharField(_('crop from'), blank=True, max_length=10, default='center', choices=CROP_ANCHOR_CHOICES)

    class Meta:
        app_label=THIS_APP

    def admin_thumbnail(self, dest_url=None):
        func = getattr(self, 'get_admin_thumbnail_url', None)
        if func is None:
            return _('An "admin_thumbnail" size has not been defined.')
        else:
            if not dest_url:
                dest_url = self.get_absolute_url()
            if hasattr(self, 'get_absolute_url'):
                return u'<a href="%s"><img src="%s"></a>' % \
                    (dest_url, func())
            else:
                return u'<a href="%s"><img src="%s"></a>' % \
                    (self.file.url, func()) if self.file else ''
    admin_thumbnail.short_description = _('Thumbnail')
    admin_thumbnail.allow_tags = True

    def cache_path(self):
        try:
            return os.path.join(os.path.dirname(self.file.path), "cache")
        except ValueError:
            ""

    def cache_url(self):
        return '/'.join([os.path.dirname(self.file.url), "cache"])

    def media_filename(self):
        return os.path.basename(force_unicode(self.file.path))

    def _get_SIZE_mediasize(self, size):
        return MediaSizeCache().sizes.get(size)

    def _get_SIZE_url(self, size):
        mediasize = MediaSizeCache().sizes.get(size)
        if not self.size_exists(mediasize):
            self.create_size(mediasize)
        if not self.file: 
            return
        if not os.path.isfile(self._get_SIZE_filename(size)):
            return
        if mediasize.increment_count:
            self.increment_count()
        return '/'.join([self.cache_url(), self._get_filename_for_size(mediasize.name)])

    def _get_SIZE_filename(self, size, *args, **kwargs):
        mediasize = MediaSizeCache().sizes.get(size)
        return smart_str(os.path.join(self.cache_path(),
                            self._get_filename_for_size(mediasize.name, *args, **kwargs)))

    def add_accessor_methods(self, *args, **kwargs):
        for size in MediaSizeCache().sizes.values():
            related_model = type(size).__name__.split('.')[-1].lower().replace('size', 'model')
            ok = False
            for anc in [x.__name__.lower() for x in type(self).mro()]:
                if anc == related_model:
                    ok = True
            if not ok:
                continue
            setattr(self, 'get_%s_size' % size.name,
                    curry(self._get_SIZE_size, size=size.name))
            setattr(self, 'get_%s_mediasize' % size.name,
                    curry(self._get_SIZE_mediasize, size=size.name))
            setattr(self, 'get_%s_url' % size.name,
                    curry(self._get_SIZE_url, size=size.name))
            setattr(self, 'get_%s_filename' % size.name,
                        curry(self._get_SIZE_filename, size=size.name))

    def _get_filename_for_size(self, size):
        size = getattr(size, 'name', size)
        base, ext = os.path.splitext(self.media_filename())
        return ''.join([base, '_', size, ext])

    def increment_count(self):
        self.view_count += 1
        models.Model.save(self)

    def size_exists(self, mediasize):
        func = getattr(self, "get_%s_filename" % mediasize.name, None)
        if func is not None:
            try:
                if os.path.isfile(func()):
                    return True
            except ValueError:
                return False
        return False

    def get_override(self, mediasize):
        """
        Returns the first MediaOverride object found for this object and mediasize.
        """
        content_type = ContentType.objects.get_for_model(self)
        overrides = MediaOverride.objects.filter(object_id=self.id, content_type=content_type, mediasize=mediasize)
        if overrides:
            return overrides[0]
        else:
            return None

    def remove_size(self, mediasize, remove_dirs=True):
        if not self.size_exists(mediasize):
            return
        filename = getattr(self, "get_%s_filename" % mediasize.name)()
        if os.path.isfile(filename):
            os.remove(filename)
        if remove_dirs:
            self.remove_cache_dirs()

    def clear_cache(self):
        # Sometimes we need not to clear caches when changing files
        prevent_cache_clear = getattr(self, 'prevent_cache_clear', False)
        if prevent_cache_clear:
            return
        cache = MediaSizeCache()
        for mediasize in cache.sizes.values():
            self.remove_size(mediasize, False)
        self.remove_cache_dirs()

    def pre_cache(self):
        cache = MediaSizeCache()
        for mediasize in cache.sizes.values():
            if mediasize.pre_cache:
                self.create_size(mediasize)

    def remove_cache_dirs(self):
        try:
            os.removedirs(self.cache_path())
        except:
            pass

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            self.date_taken = now()
        if self._get_pk_val():
            remove_deleted = getattr(self, 'remove_deleted', PHOTOLOGUE_REMOVE_DELETED)
            orig = MediaModel.objects.get(pk=self.pk)
            if remove_deleted and orig.file.path != self.file.path:
                # Try deleting original video
                try:
                    os.remove(orig.file.path)
                except:
                    pass
                orig.prevent_cache_clear = getattr(self, 'prevent_cache_clear', False)
                orig.clear_cache()
        super(MediaModel, self).save(*args, **kwargs)
        self.pre_cache()

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        self.clear_cache()
        remove_deleted = getattr(self, 'remove_deleted', PHOTOLOGUE_REMOVE_DELETED)
        try:
            if remove_deleted:
                os.remove(self.file.path)
        except:
            pass
        super(MediaModel, self).delete()

class MediaOverride(MediaModel):
    content_type = models.ForeignKey('contenttypes.ContentType')
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey("content_type", "object_id")
    mediasize = models.ForeignKey('MediaSize', blank=False)

    class Meta:
        app_label=THIS_APP

class MediaSize(models.Model):
    name = models.CharField(_('name'), max_length=64, unique=False, help_text=_('Size name should contain only letters, numbers and underscores. Examples: "thumbnail", "display", "small", "main_page_widget".'))
    width = models.PositiveIntegerField(_('width'), default=0, help_text=_('If width is set to "0" the media will be scaled to the supplied height.'))
    height = models.PositiveIntegerField(_('height'), default=0, help_text=_('If height is set to "0" the media will be scaled to the supplied width'))
    upscale = models.BooleanField(_('upscale media?'), default=False, help_text=_('If selected the media will be scaled up if necessary to fit the supplied dimensions. Cropped sizes will be upscaled regardless of this setting.'))
    crop = models.BooleanField(_('crop to fit?'), default=False, help_text=_('If selected the media will be scaled and cropped to fit the supplied dimensions.'))
    pre_cache = models.BooleanField(_('pre-cache?'), default=False, help_text=_('If selected this media size will be pre-cached as media are added.'))
    increment_count = models.BooleanField(_('increment view count?'), default=False, help_text=_('If selected the "view_count" will be incremented when this size is displayed.'))

    class Meta:
        app_label=THIS_APP

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    def validate_unique(self, exclude=None):
        # Check as usual
        try:
            super(MediaSize, self).validate_unique(exclude)
            # No erros
            errors = {}
        except ValidationError, errors:
            # Save the error in errors
            pass
        # Check for unique name
        qs = type(self).objects.filter(name = self.name)
        # Exclude the current object from the query if we are editing an
        # instance (as opposed to creating a new one)
        if not self._state.adding and self.pk is not None:
            qs = qs.exclude(pk=self.pk)
        # Is anything here?
        if qs.exists():
            errors.setdefault('name', []).append(self.unique_error_message(type(self), ['name']))
        # Raise errors as usual
        if errors:
            raise ValidationError(errors)

    def clear_cache(self):
        for cls in MediaModel.__subclasses__():
            if not cls._meta.abstract:
                for obj in cls.objects.all():
                    obj.remove_size(self)
                    if self.pre_cache:
                        obj.create_size(self)
        MediaSizeCache().reset()

    def save(self, *args, **kwargs):
        if self.crop is True:
            if self.width == 0 or self.height == 0:
                raise ValueError("MediaSize width and/or height can not be zero if crop=True.")
        super(MediaSize, self).save(*args, **kwargs)
        MediaSizeCache().reset()
        self.clear_cache()

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        self.clear_cache()
        super(MediaSize, self).delete()

    def _get_size(self):
        return (self.width, self.height)
    def _set_size(self, value):
        self.width, self.height = value
    size = property(_get_size, _set_size)


class MediaSizeCache(object):
    __state = {"sizes": {}}

    def __init__(self):
        self.__dict__ = self.__state
        if not len(self.sizes):
            sizes = MediaSize.objects.all()
            for size in sizes:
                related = False
                for subclass in size._meta.get_all_related_objects():
                    name = subclass.get_accessor_name()
                    if name.endswith('size') and hasattr(size, name):
                        if not related:
                            related = getattr(size, name)
                if related:
                    self.sizes[size.name] = related
                else:
                    self.sizes[size.name] = size

    def reset(self):
        self.sizes = {}

class BaseEffect(models.Model):
    name = models.CharField(_('name'), max_length=50, unique=True)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        app_label=THIS_APP
        abstract = True

    def sample_dir(self):
        return os.path.join(settings.MEDIA_ROOT, PHOTOLOGUE_DIR, 'samples')

    def admin_sample(self):
        return u'<img src="%s">' % self.sample_url()
    admin_sample.short_description = 'Sample'
    admin_sample.allow_tags = True

    def pre_process(self, im):
        return im

    def post_process(self, im):
        return im

    def process(self, im):
        im = self.pre_process(im)
        im = self.post_process(im)
        return im

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        try:
            os.remove(self.sample_filename())
        except:
            pass
        models.Model.save(self, *args, **kwargs)
        self.create_sample()
        #FIXME
        for size in self.photo_sizes.all():
            size.clear_cache()
        # try to clear all related subclasses of ImageModel
        for prop in [prop for prop in dir(self) if prop[-8:] == '_related']:
            for obj in getattr(self, prop).all():
                obj.clear_cache()
                obj.pre_cache()

    def delete(self):
        try:
            os.remove(self.sample_filename())
        except:
            pass
        models.Model.delete(self)
