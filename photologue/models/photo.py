from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from photologue.default_settings import *
from image import ImageModel
from gallery import GalleryItemBase

class Photo(ImageModel, GalleryItemBase):
    class Meta:
        verbose_name = _("photo")
        verbose_name_plural = _("photos")

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.EXIF.get('EXIF DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(int(year), int(month), int(day),
                                               int(hour), int(minute), int(second))
            except:
                pass
        super(Photo, self).save(*args, **kwargs)
#Photo._meta.get_field('file').verbose_name = _('Photo file')
