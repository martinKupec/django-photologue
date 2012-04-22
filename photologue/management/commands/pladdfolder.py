import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify

from photologue.models import Gallery, GalleryItemBase, Video, Photo
from photologue.default_settings import *
from photologue.utils.video import video_sizes
from photologue.utils.upload import upload_file

try:
    import Image
except ImportError:
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")

class Command(BaseCommand):
    help = _('Copy content of selected folder to media folder and add to database.')
    args = _('folder [gallery]')

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args) < 1:
            return _('Need a folder to work on.')
        return add_folder(*args) + '\n'

def add_folder(folder, gallery=None):
    """
    Scan media upload folder and add any missing gallery items.
    """

    if not os.path.isdir(folder):
        return _("Provided folder is not a valid folder.")

    if gallery:
        try:
            gallery = Gallery.objects.get(title=gallery)
        except Gallery.DoesNotExist:
            return _("Provided gallery title does not exists.")

    def read_file(filename):
        try:
            full = os.path.join(folder, filename)
            with open(full, 'rb') as f:
                return f.read()
        except:
            return None
        
    for filename in os.listdir(folder):
        full = os.path.join(folder, filename)
        if not os.path.isfile(full):
            continue
        file_mtime = datetime.fromtimestamp(os.path.getmtime(full))
        if not is_aware(file_mtime):
            file_mtime = make_aware(file_mtime, get_current_timezone())
        with open(full, 'rb') as f:
            upload_file(filename, filename, f, file_mtime, read_file, None, gallery)
    return _('Done')
