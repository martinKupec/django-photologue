import os
import datetime
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone
from django.utils.functional import curry

from photologue.default_settings import *
from photologue.utils.video import video_info, video_calculate_size
from media import *
from image import ImageModel, ImageSize
from gallery import GalleryItemBase

try:
    from dateutil import parser
    dateutil = True
except ImportError:
    dateutil = False

VIDEO_TYPES = (
    ('mp4', 'MPEG-4', 'video/mp4'),
    ('ogv', 'Vorbis', 'video/ogg'),
    ('flv', 'Flash', 'video/flv'),
    ('webm', 'WebM', 'video/webm'),
)

def poster_unconverted(poster):
    #FIXME move to STATIC - need to fix cache system
    unconverted = os.path.join(settings.MEDIA_ROOT, DEFAULT_POSTER_PATH)
    if poster.file.path != unconverted:
        return False
    return True

class VideoModel(MediaModel):
    poster = models.OneToOneField(ImageModel, null=True, editable=False)
    width = models.PositiveIntegerField(_('original video width'), editable=False)
    height = models.PositiveIntegerField(_('original video height'), editable=False)
    duration = models.PositiveIntegerField(_('video duration'), editable=False)

    class Meta:
        app_label=THIS_APP

    def save(self, *args, **kwargs):
        if not self.date_taken and dateutil:
            # We have no access to any date information as
            # video files usually don't bundle it
            # all we can do is to try to get the date from filename
            date = None
            name = os.path.basename(self.file.path)
            name = name.rpartition('.')[0]
            # Try just whole name without extention
            try:
                date = parser.parse(name)
            except:
                pass
            # Try stripping the non-numeric start
            if not date:
                try:
                    for i in xrange(len(name)):
                        if name[i] in "0123456789":
                            name = name[i:]
                            break
                    date = parser.parse(name)
                except:
                    pass
            # We may have added _X, for some X as sequencial number, strip it
            if not date:
                try:
                    name = name.rpartition('_')[0]
                    date = parser.parse(name)
                except:
                    pass
            # Check is the date is sane
            if date and date > datetime.datetime(2000, 1, 1):
                # Win
                if not is_aware(date):
                    date = make_aware(date, get_current_timezone())
                self.date_taken = date
        # Add attribute if missing - we need it here
        prevent_cache_clear = getattr(self, 'prevent_cache_clear', False)
        # Do we have original?
        if not self._get_pk_val():
            orig = False
        else:
            try:
                orig = VideoModel.objects.get(id=self.videomodel_ptr_id)
            except VideoModel.DoesNotExist:
                orig = False

        # Have we changed the file?
        if orig and orig.file == self.file:
            self.prevent_cache_clear = True
        elif not prevent_cache_clear:
            if self.poster and not poster_unconverted(self.poster):
                # Change the file path
                self.poster.file = DEFAULT_POSTER_PATH
                # Save poster - this will delete old poster and clear cache
                self.poster.save()
            # Get the basic informations about the video
            info = video_info(self.file.path)
            self.width = info[0]
            self.height = info[1]
            self.duration = info[3]
            self.view_count = 0
        # Do we have poster?
        if not self.poster:
            poster = ImageModel(file=DEFAULT_POSTER_PATH)
            poster.save()
            self.poster = poster
        super(VideoModel, self).save(*args, **kwargs)
    
    def delete(self):
        if self.poster:
            poster = self.poster
        else:
            poster = False
        # Delete the video first
        # We need to do it this way,
        # as poster cascades deletion to video
        super(VideoModel, self).delete()
        # Now delete poster if needed
        if poster:
            if poster_unconverted(poster):
                poster.remove_deleted = False
            poster.delete()

    def convertion_unfinished(self):
        return VideoConvert.objects.filter(video=self, converted=False).exists()

    def _get_SIZE_size(self, size):
        mediasize = MediaSizeCache().sizes.get(size)
        if not self.size_exists(mediasize):
            self.create_size(mediasize)
        try:
            width, height = video_calculate_size(self, mediasize)
            if self._get_filename_for_size(mediasize) == 'unconverted':
                return
        except Exception, e:
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
    deinterlace = models.BooleanField(_('deinterlace?'), default=True, help_text=_('If enabled use deinterlace filter\
                    when not able to recognice video type(sadly most cases)'))
    videobitrate = models.PositiveIntegerField(_('video bitrate (kbps)'), default=1000, help_text=_('Video bitrate in kilobits per second.'))
    audiobitrate = models.PositiveIntegerField(_('audio bitrate (kbps)'), default=128, help_text=_('Audio bitrate in kilobits per second.\
                    When set to 0, it will mute audio.'))

    class Meta:
        app_label=THIS_APP
        ordering = ['width', 'height']
        verbose_name = _('video size')
        verbose_name_plural = _('video sizes')

    def save(self, *args, **kwargs):
        if not self.pre_cache:
            self.pre_cache = True
        MediaSizeCache().reset()
        # Skip MediaSize save - prevent clearing caches
        super(MediaSize, MediaSize).save(self, *args, **kwargs)

    def validate_unique(self, exclude=None):
        # Check as usual
        errors = {}
        try:
            super(VideoSize, self).validate_unique(exclude)
        except ValidationError, e:
            # Save the error in errors
            errors = e.update_error_dict(errors)

        # Check for insane setting
        if self.letterbox == True and self.crop == True:
            errors.setdefault('letterbox', []).append(_("cannot be true both letterbox and crop."))
            errors.setdefault('crop', []).append(     _("cannot be true both letterbox and crop."))
        if self.letterbox == True:
            if self.width == 0 or self.height == 0:
                errors.setdefault('letterbox', []).append(_("width and/or height can not be zero if letterbox=true."))
        # Raise errors as usual
        if errors:
            raise ValidationError(errors)

    def source_type(self):
        types = dict(zip(map(lambda x: x[0], VIDEO_TYPES), map(lambda x: x[2], VIDEO_TYPES)))
        return types[self.videotype]


class VideoConvert(models.Model):
    video = models.ForeignKey(VideoModel, help_text=_('video to convert'), blank=False, null=False)
    videosize = models.ForeignKey(VideoSize, help_text=_('video size to use'), null=False, blank=False)
    access_date = models.DateTimeField(_('access date'), auto_now=True, help_text=_('This date changes on each access to this object'))
    time = models.BigIntegerField(_('convertion time'), help_text=_('this is the time the conversion took.'), default=0, blank=True)
    inprogress = models.BooleanField(_('in progress'))
    converted = models.BooleanField(_('converted'))
    message = models.TextField(_('message'), null=True, blank=True)

    class Meta:
        app_label=THIS_APP
        ordering = ['-video__date_taken']
        verbose_name = _("video convert")
        verbose_name_plural = _("video converts")

    def __unicode__(self):
        return unicode(self.video)

class Video(GalleryItemBase, VideoModel):
    class Meta:
        app_label=THIS_APP
        verbose_name = _("video")
        verbose_name_plural = _("videos")
        ordering = ['-date_taken']
