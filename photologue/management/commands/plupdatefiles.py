import os
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import File
from django.core.files.move import file_move_safe
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone, localtime
from django.template.defaultfilters import slugify

from photologue.models import MediaSize, MediaModel, GalleryItemBase, Video, Photo, MediaSizeCache
from photologue.default_settings import *
from photologue.utils.video import video_sizes
from photologue.utils.upload import move_file
from photologue.models.video import poster_unconverted

class Command(BaseCommand):
    help = _('Set name and mtime of all files associated to media items to title_slug and date_taken.')

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return update_files()

def update_item(item, newname):
        file_root = os.path.join(settings.MEDIA_ROOT, get_storage_path(item, ''))
        path = item.file.path
        if not os.path.exists(path):
            print item.title, ": files doesn't exist: ", path
            return
        root, name = os.path.split(path)
        base, ext = os.path.splitext(name)
        renamed = os.path.join(root, u'%s%s' % (newname, ext))

        cache = {}
        for size in MediaSizeCache().sizes.values():
            func = getattr(item, "get_%s_filename" % size.name, None)
            if func:
                sizename = func()
                if os.path.exists(sizename) and sizename.startswith(file_root):
                    cache[func] = sizename

        # Do the move and save
        move_file(item, path, renamed)
        # No need to regenerate caches
        item.prevent_cache_clear = True
        item.prevent_delete = True
        item.save()

        for key, value in cache.items():
            target = key()
            if not target.endswith('unconverted') and os.path.exists(value):
                file_move_safe(value, target)

        taken = item.date_taken
        taken = taken.astimezone(get_current_timezone())
        mtime = int(time.mktime(taken.timetuple()))
        os.utime(item.file.path, (mtime, mtime))


def update_files():
    """
    Set name and mtime of all files associated to media items to title_slug and date_taken.
    """

    for item in GalleryItemBase.objects.all():
        update_item(item, item.title_slug)
        if hasattr(item, 'poster'):
            if not poster_unconverted(item.poster):
                update_item(item.poster, item.title_slug)
