from django.db import models
from django.utils.translation import ugettext_lazy as _

from photologue.default_settings import *

from image import ImageModel
from gallery import GalleryItemBase

class Photo(ImageModel, GalleryItemBase):
    class Meta:
        app_label=THIS_APP
        verbose_name = _("photo")
        verbose_name_plural = _("photos")
