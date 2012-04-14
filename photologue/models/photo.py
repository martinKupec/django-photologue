from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from photologue.default_settings import *
from image import ImageModel
from gallery import GalleryItemBase

class PhotoManager(models.Manager):
    def latest(self, limit=LATEST_LIMIT, public=True):
        if public:
            photo_set = self.public()
        else:
            photo_set = self.all()
        if limit == 0:
            return photo_set
        return photo_set[:limit]

    def photo_count(self, is_public=True):
        if is_public:
            return self.public().count()
        else:
            return self.count()

    def public(self):
        return self.filter(is_public=True)

    def sample(self, count=0, public=True):
        if public:
            photo_set = self.public().order_by('?')
        else:
            photo_set = self.order_by('?')
        if count == 0:
            return photo_set
        return photo_set[:count]

class Photo(ImageModel, GalleryItemBase):
    objects = PhotoManager()

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
