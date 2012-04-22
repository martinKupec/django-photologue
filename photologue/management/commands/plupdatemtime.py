import os
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone, localtime
from django.template.defaultfilters import slugify

from photologue.models import MediaSize, MediaModel, GalleryItemBase, Video, Photo
from photologue.default_settings import *
from photologue.utils.video import video_sizes

class Command(BaseCommand):
    help = _('Set mtime of all files associated to media items to date_taken.')

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return update_mtime()

def update_mtime():
    """
    Scan media upload folder and add any missing gallery items.
    """

    for item in MediaModel.objects.all():
        path = item.file.path
        taken = item.date_taken
        taken = taken.astimezone(get_current_timezone())
        mtime = int(time.mktime(taken.timetuple()))
        os.utime(path, (mtime, mtime))
