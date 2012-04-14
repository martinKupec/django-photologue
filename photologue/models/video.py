from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_init, post_save
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from photologue.default_settings import *
from media import *
from image import ImageModel
from gallery import GalleryItemBase

""" Use signals to add videos to ConvertVideo for batch processing """

def set_original(sender, instance, **kwargs):
    try:
        instance.last_file = unicode(instance.file)
    except KeyError:
        instance.last_file = None

def add_convert(sender, instance, created, **kwargs):
    if instance.file != instance.last_file or created:
        ctype = ContentType.objects.get_for_model(sender)
        c = ConvertVideo.objects.create(content_type=ctype, object_id=instance.pk, converted=False, message='', videosize=None)

""" Register signals to any base of VideoModel using a metaclass """
class VideoModelBase(ModelBase):

    def __new__(cls, name, bases, attrs):
        new = super(VideoModelBase, cls).__new__(cls, name, bases, attrs)
        if not new._meta.abstract:
            post_init.connect(set_original, sender=new)
            post_save.connect(add_convert, sender=new)
        return new

class VideoModel(MediaModel):
    __metaclass__ = VideoModelBase

    poster = models.OneToOneField(ImageModel, null=True)
    mp4_video = models.FileField(_('mp4 video'), null=True, upload_to=get_storage_path)
    ogv_video = models.FileField(_('ogv video'), null=True, upload_to=get_storage_path)
    flv_video = models.FileField(_('flv video'), null=True, upload_to=get_storage_path)
    webm_video= models.FileField(_('webm video'),null=True, upload_to=get_storage_path)

    def save(self, *args, **kwargs):
        if not self.poster:
            self.poster = ImageModel.objects.create(file=DEFAULT_POSTER_PATH)
        super(VideoModel, self).save(*args, **kwargs)
    
    def delete(self):
        if self.poster:
            self.poster.delete()
        super(VideoModel, self).delete()

    def get_absolute_url(self):
        return reverse('pl-video', args=[self.title_slug])

    def create_size(self, videosize):
        # Fail gracefully if we don't have an video.
        if not self.original_video:
            return

        if self.size_exists(videosize):
            return
        if not os.path.isdir(self.cache_path()):
            os.makedirs(self.cache_path())

        # check if we have overrides and use that instead
        override = self.get_override(videosize)
        video_model_obj = override if override else self

        ctype = ContentType.objects.get_for_model(self)
        c = ConvertVideo.objects.create(content_type=ctype, object_id=instance.pk, converted=False, message='', videosize=videosize)

class VideoSize(MediaSize):

    def save(self, *args, **kwargs):
        if not self.pre_cache:
            self.pre_cache = True
        super(VideoSize, self).save(*args, **kwargs)

    class Meta:
        ordering = ['width', 'height']
        verbose_name = _('video size')
        verbose_name_plural = _('video sizes')

class ConvertVideo(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    video = generic.GenericForeignKey('content_type', 'object_id')
    message = models.TextField(null=True, blank=True)
    converted = models.BooleanField()
    videosize = models.ForeignKey(VideoSize, null=True, blank=True)

    def __unicode__(self):
        return unicode(self.video)

class Video(VideoModel, GalleryItemBase):
    class Meta:
        verbose_name = _("video")
        verbose_name_plural = _("videos")

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                #exif_date = self.EXIF.get('EXIF DateTimeOriginal', None)
                #if exif_date is not None:
                #    d, t = str.split(exif_date.values)
                #    year, month, day = d.split(':')
                #    hour, minute, second = t.split(':')
                #   self.date_taken = datetime(int(year), int(month), int(day),
                #                               int(hour), int(minute), int(second))
                pass
            except:
                pass
        super(Video, self).save(*args, **kwargs)
#Video._meta.get_field('file').verbose_name = _('Video file')
