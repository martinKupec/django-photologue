from inspect import isclass
from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import make_aware, get_current_timezone
from django.core.urlresolvers import reverse

from photologue.default_settings import *
from photologue.utils import EXIF
from photologue.utils.reflection import add_reflection
from photologue.utils.watermark import apply_watermark
from media import *

import photologue.utils as utils

# Required PIL classes may or may not be available from the root namespace
# depending on the installation method used.
try:
    import Image
    import ImageFile
    import ImageFilter
    import ImageEnhance
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
    except ImportError:
        raise ImportError('Photologue was unable to import the Python Imaging Library. Please confirm it`s installed and available on your current Python path.')

# Set MAXBLOCK from settings
ImageFile.MAXBLOCK = MAXBLOCK

# Prepare a list of image filters
filter_names = []
for n in dir(ImageFilter):
    klass = getattr(ImageFilter, n)
    if isclass(klass) and issubclass(klass, ImageFilter.BuiltinFilter) and \
        hasattr(klass, 'name'):
            filter_names.append(klass.__name__)
IMAGE_FILTERS_HELP_TEXT = _('Chain multiple filters using the following pattern "FILTER_ONE->FILTER_TWO->FILTER_THREE". Image filters will be applied in order. The following filters are available: %s.' % (', '.join(filter_names)))

class ImageModel(MediaModel):
    effect = models.ForeignKey('ImageEffect', null=True, blank=True, related_name="%(class)s_related", verbose_name=_('effect'))

    class Meta:
        app_label=THIS_APP

    @property
    def EXIF(self):
        try:
            return EXIF.process_file(open(self.file.path, 'rb'))
        except:
            try:
                return EXIF.process_file(open(self.file.path, 'rb'), details=False)
            except:
                return {}

    def save(self, *args, **kwargs):
        # Save the original date
        # this can be None, after save it is changed by underlaying models
        date_taken = self.date_taken
        # We have to save first,
        # this will update the file.path to right location
        super(ImageModel, self).save(*args, **kwargs)
        if date_taken is None:
            try:
                exif_date = self.EXIF.get('EXIF DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    taken = datetime(int(year), int(month), int(day),
                                               int(hour), int(minute), int(second))
                    self.date_taken = make_aware(taken, get_current_timezone())
                    super(ImageModel, self).save(*args, **kwargs)
            except Exception, e:
                pass

    def _get_SIZE_size(self, size):
        mediasize = MediaSizeCache().sizes.get(size)
        if not self.size_exists(mediasize):
            self.create_size(mediasize)
        sizes = Image.open(self._get_SIZE_filename(size)).size
        return {'width': sizes[0], 'height': sizes[1]}

    def create_size(self, mediasize):
        # Fail gracefully if we don't have an image.
        if not self.file:
            return

        # Check if we got right size
        if not hasattr(mediasize, 'imagesize'):
            return
        imagesize = mediasize.imagesize

        if self.size_exists(imagesize):
            return
        if not os.path.isdir(self.cache_path()):
            os.makedirs(self.cache_path())

        # check if we have overrides and use that instead
        override = self.get_override(imagesize)
        image_model_obj = override if override else self

        try:
            im = Image.open(image_model_obj.file.path)
        except IOError:
            return
        # Correct colorspace
        im = utils.colorspace(im)
        # Save the original format
        im_format = im.format
        # Apply effect if found
        if image_model_obj.effect is not None:
            im = image_model_obj.effect.pre_process(im)
        elif imagesize.effect is not None:
            im = imagesize.effect.pre_process(im)
        # Resize/crop image
        if im.size != imagesize.size and imagesize.size != (0, 0):
            im = image_model_obj.resize_image(im, imagesize)
        # Apply watermark if found
        if imagesize.watermark is not None:
            im = imagesize.watermark.post_process(im)
        # Save file
        im_filename = getattr(self, "get_%s_filename" % imagesize.name)()
        try:
            if im_format != 'JPEG':
                im.save(im_filename)
            im.save(im_filename, 'JPEG', quality=int(imagesize.quality), optimize=True)
        except IOError, e:
            if os.path.isfile(im_filename):
                os.unlink(im_filename)
            raise e

    def resize_image(self, im, imagesize):
        cur_width, cur_height = im.size
        new_width, new_height = imagesize.size
        if imagesize.crop:
            ratio = max(float(new_width)/cur_width,float(new_height)/cur_height)
            x = (cur_width * ratio)
            y = (cur_height * ratio)
            xd = abs(new_width - x)
            yd = abs(new_height - y)
            x_diff = int(xd / 2)
            y_diff = int(yd / 2)
            if self.crop_from == 'top':
                box = (int(x_diff), 0, int(x_diff+new_width), new_height)
            elif self.crop_from == 'left':
                box = (0, int(y_diff), new_width, int(y_diff+new_height))
            elif self.crop_from == 'bottom':
                box = (int(x_diff), int(yd), int(x_diff+new_width), int(y)) # y - yd = new_height
            elif self.crop_from == 'right':
                box = (int(xd), int(y_diff), int(x), int(y_diff+new_height)) # x - xd = new_width
            else:
                box = (int(x_diff), int(y_diff), int(x_diff+new_width), int(y_diff+new_height))
            im = im.resize((int(x), int(y)), Image.ANTIALIAS).crop(box)
        else:
            if not new_width == 0 and not new_height == 0:
                ratio = min(float(new_width)/cur_width,
                            float(new_height)/cur_height)
            else:
                if new_width == 0:
                    ratio = float(new_height)/cur_height
                else:
                    ratio = float(new_width)/cur_width
            new_dimensions = (int(round(cur_width*ratio)),
                              int(round(cur_height*ratio)))
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not imagesize.upscale:
                    return im
            im = im.resize(new_dimensions, Image.ANTIALIAS)
        return im

class ImageSize(MediaSize):
    effect = models.ForeignKey('ImageEffect', null=True, blank=True, related_name='media_sizes', verbose_name=_('image effect'))
    quality = models.PositiveIntegerField(_('quality'), choices=JPEG_QUALITY_CHOICES, default=70, help_text=_('JPEG image quality.'))
    watermark = models.ForeignKey('Watermark', null=True, blank=True, related_name='media_sizes', verbose_name=_('watermark image'))

    class Meta:
        app_label=THIS_APP
        ordering = ['width', 'height']
        verbose_name = _('image size')
        verbose_name_plural = _('image sizes')

class ImageBaseEffect(BaseEffect):
    class Meta:
        app_label=THIS_APP

    def sample_url(self):
        return settings.MEDIA_URL + '/'.join([PHOTOLOGUE_DIR, 'samples', '%s %s.jpg' % (self.name.lower(), 'sample')])

    def sample_filename(self):
        return os.path.join(self.sample_dir(), '%s %s.jpg' % (self.name.lower(), 'sample'))

    def create_sample(self):
        if not os.path.isdir(self.sample_dir()):
            os.makedirs(self.sample_dir())
        try:
            im = Image.open(SAMPLE_IMAGE_PATH)
        except IOError:
            raise IOError('Photologue was unable to open the sample image: %s.' % SAMPLE_IMAGE_PATH)
        im = self.process(im)
        im.save(self.sample_filename(), 'JPEG', quality=90, optimize=True)

class ImageEffect(ImageBaseEffect):
    """ A pre-defined effect to apply to images """
    transpose_method = models.CharField(_('rotate or flip'), max_length=15, blank=True, choices=IMAGE_TRANSPOSE_CHOICES)
    color = models.FloatField(_('color'), default=1.0, help_text=_("A factor of 0.0 gives a black and white image, a factor of 1.0 gives the original image."))
    brightness = models.FloatField(_('brightness'), default=1.0, help_text=_("A factor of 0.0 gives a black image, a factor of 1.0 gives the original image."))
    contrast = models.FloatField(_('contrast'), default=1.0, help_text=_("A factor of 0.0 gives a solid grey image, a factor of 1.0 gives the original image."))
    sharpness = models.FloatField(_('sharpness'), default=1.0, help_text=_("A factor of 0.0 gives a blurred image, a factor of 1.0 gives the original image."))
    filters = models.CharField(_('filters'), max_length=200, blank=True, help_text=_(IMAGE_FILTERS_HELP_TEXT))
    reflection_size = models.FloatField(_('size'), default=0, help_text=_("The height of the reflection as a percentage of the orignal image. A factor of 0.0 adds no reflection, a factor of 1.0 adds a reflection equal to the height of the orignal image."))
    reflection_strength = models.FloatField(_('strength'), default=0.6, help_text=_("The initial opacity of the reflection gradient."))
    background_color = models.CharField(_('color'), max_length=7, default="#FFFFFF", help_text=_("The background color of the reflection gradient. Set this to match the background color of your page."))

    class Meta:
        app_label=THIS_APP
        verbose_name = _("image effect")
        verbose_name_plural = _("image effects")

    def pre_process(self, im):
        if self.transpose_method != '':
            method = getattr(Image, self.transpose_method)
            im = im.transpose(method)
        if im.mode != 'RGB' and im.mode != 'RGBA':
            return im
        for name in ['Color', 'Brightness', 'Contrast', 'Sharpness']:
            factor = getattr(self, name.lower())
            if factor != 1.0:
                im = getattr(ImageEnhance, name)(im).enhance(factor)
        for name in self.filters.split('->'):
            image_filter = getattr(ImageFilter, name.upper(), None)
            if image_filter is not None:
                try:
                    im = im.filter(image_filter)
                except ValueError:
                    pass
        return im

    def post_process(self, im):
        if self.reflection_size != 0.0:
            im = add_reflection(im, bgcolor=self.background_color, amount=self.reflection_size, opacity=self.reflection_strength)
        return im

class Watermark(ImageBaseEffect):
    image = models.ImageField(_('image'), upload_to=PHOTOLOGUE_DIR+"/watermarks")
    style = models.CharField(_('style'), max_length=5, choices=WATERMARK_STYLE_CHOICES, default='scale')
    opacity = models.FloatField(_('opacity'), default=1, help_text=_("The opacity of the overlay."))

    class Meta:
        app_label=THIS_APP
        verbose_name = _('watermark')
        verbose_name_plural = _('watermarks')

    def post_process(self, im):
        mark = Image.open(self.image.path)
        return apply_watermark(im, mark, self.style, self.opacity)
