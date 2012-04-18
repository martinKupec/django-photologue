import os
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from django.utils.functional import curry

from photologue.default_settings import *
from photologue.utils.video import video_sizes
from media import *
from image import ImageModel, ImageSize
from gallery import GalleryItemBase

VIDEO_TYPES = (
    ('mp4', 'MPEG-4', 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
    ('ogv', 'Vorbis', 'video/ogg; codecs="theora, vorbis"'),
    ('flv', 'Flash', 'video/flv'),
    ('webm', 'WebM', 'video/webm; codecs="vp8, vorbis"'),
)

def poster_unconverted(poster):
    #FIXME move to STATIC - need to fix cache system
    unconverted = os.path.join(settings.MEDIA_ROOT, DEFAULT_POSTER_PATH)
    if poster.file.path != unconverted:
        return False
    return True

class VideoModel(MediaModel):
    poster = models.OneToOneField(ImageModel, null=True)

    def save(self, *args, **kwargs):
        try:
            orig = VideoModel.objects.get(pk=self.pk)
            if orig.file == self.file:
                self.prevent_cache_clear = True
            else:
                if self.poster and not poster_unconverted(self.poster):
                    self.poster.delete()
                    self.poster = None
                self.prevent_cache_clear = False
                self.view_count = 0
        except VideoModel.DoesNotExist:
            pass
        if not self.poster:
            self.poster = ImageModel.objects.create(file=DEFAULT_POSTER_PATH)
        super(VideoModel, self).save(*args, **kwargs)
    
    def delete(self):
        if self.poster:
            self.poster.delete()
        super(VideoModel, self).delete()

    def __unicode__(self):
        return unicode(os.path.split(self.file.path)[1])

    def convertion_unfinished(self):
        return VideoConvert.objects.filter(video=self, converted=False).exists()

    def _get_SIZE_size(self, size):
        mediasize = MediaSizeCache().sizes.get(size)
        if not self.size_exists(mediasize):
            self.create_size(mediasize)
        try:
            width, height, aspect = video_sizes(self._get_SIZE_filename(size))
        except:
            return
        return {'width': width, 'height': height}

    def _get_filename_for_size(self, size, invalid_ok=False):
        if hasattr(size, 'name'):
            # size is class
            size_name = size.name
            mediasize = size
        else:
            # size is name
            size_name = size
            mediasize = self._get_SIZE_mediasize(size)
        if not invalid_ok and VideoConvert.objects.filter(video=self, videosize=mediasize, converted=False).exists():
            return "unconverted"
        base, ext = os.path.splitext(self.media_filename())
        return ''.join([base, '_', size_name, '.', mediasize.videotype])

    def add_accessor_methods(self, *args, **kwargs):
        super(VideoModel, self).add_accessor_methods(*args, **kwargs)
        if not self.poster:
            return
        for size in MediaSizeCache().sizes.values():
            if type(size) != ImageSize:
                continue
            for func in ['get_%s_size', 'get_%s_mediasize', 'get_%s_url', 'get_%s_filename']:
                func = func % size.name
                if not hasattr(self, func):
                    setattr(self, func, curry(getattr(self.poster, func)))

    def create_size(self, mediasize):
        # Fail gracefully if we don't have an video.
        if not self.file:
            return

        # Check if we got right size
        if not hasattr(mediasize, 'videosize'):
            return
        videosize = mediasize.videosize

        if self.size_exists(videosize):
            return
        if not os.path.isdir(self.cache_path()):
            os.makedirs(self.cache_path())

        # check if we have overrides and use that instead
        override = self.get_override(videosize)
        video_model_obj = override if override else self

        if not VideoConvert.objects.filter(video=video_model_obj, videosize=videosize).exists():
            c = VideoConvert.objects.create(video=video_model_obj, videosize=videosize, converted=False, message='')

    def remove_size(self, videosize, *args, **kwargs):
        c = VideoConvert.objects.filter(video=self, videosize=videosize)
        c.delete()
        super(VideoModel, self).remove_size(videosize, *args, **kwargs)

class VideoSize(MediaSize):
    videotype = models.CharField(_('type'), max_length=4, choices=map(lambda x: (x[0], x[1]), VIDEO_TYPES), null=False, blank=False,
                help_text=_('This is video format for this video size.'))
    twopass = models.BooleanField(_('two pass?'), default=True, help_text=_('If selected, the conversion will be performed in two passes,\
                    it is slower, but the result is generally better.'))
    letterbox = models.BooleanField(_('letterbox'), default=True, help_text=_('If enabled and aspect ratio is not matching,\
                    put the video in black box.'))
    videobitrate = models.PositiveIntegerField(_('video bitrate (kbps)'), default=2000, help_text=_('Video bitrate in kilobits per second.'))
    audiobitrate = models.PositiveIntegerField(_('audio bitrate'), default=32000, help_text=_('Audio bitrate in bits per second.\
                    When set to 0, it will mute audio.'))

    def save(self, *args, **kwargs):
        if not self.pre_cache:
            self.pre_cache = True
        super(VideoSize, self).save(*args, **kwargs)

    def source_type(self):
        types = dict(zip(map(lambda x: x[0], VIDEO_TYPES), map(lambda x: x[2], VIDEO_TYPES)))
        return types[self.videotype]

    class Meta:
        ordering = ['width', 'height']
        verbose_name = _('video size')
        verbose_name_plural = _('video sizes')

class VideoConvert(models.Model):
    video = models.ForeignKey(VideoModel, help_text=_('video to convert'), blank=False, null=False)
    videosize = models.ForeignKey(VideoSize, help_text=_('video size to use'), null=False, blank=False)
    access_date = models.DateTimeField(_('access date'), auto_now=True, help_text=_('This date changes on each access to this object'))
    time = models.BigIntegerField(_('convertion time'), help_text=_('this is the time the conversion took.'), default=0, blank=True)
    inprogress = models.BooleanField(_('in progress'))
    converted = models.BooleanField(_('converted'))
    message = models.TextField(_('message'), null=True, blank=True)

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
