import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone
from django.template.defaultfilters import slugify

from photologue.models import MediaSize, MediaModel, GalleryItemBase, Video, Photo
from photologue.default_settings import *
from photologue.utils.video import video_sizes

try:
    import Image
except ImportError:
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")

class Command(BaseCommand):
    help = _('Scan media upload folder and add any missing gallery items.')

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return refresh_media()

class TemporaryFile(File):
    def temporary_file_path(self):
        return self.file.name

class OverrideStorage(FileSystemStorage):
    def get_available_name(self, name):
        return name

def refresh_media():
    """
    Scan media upload folder and add any missing gallery items.
    """

    itemized = map(lambda o: o.file.path, MediaModel.objects.all())

    my_root = os.path.join(settings.MEDIA_ROOT, PHOTOLOGUE_DIR)
    for root, dirs, files in os.walk(my_root):
        # First filter out cache directories
        try:
            dirs.remove('cache')
        except:
            pass
        # Go througth files
        for fn in files:
            full = os.path.join(root, fn)
            if full in itemized:
                continue
            date_taken = datetime.fromtimestamp(os.path.getmtime(full))
            if not is_aware(date_taken):
                date_taken = make_aware(date_taken, get_current_timezone())

            # Next part is taken from process_zipfile
            filetype = False
            # Is it an image?
            try:
                trial_image = Image.open(full)
                trial_image.load()
                trial_image = Image.open(full)
                trial_image.verify()
                filetype = 'image'
            except Exception, e:
                pass
            # Is it a video?
            if not filetype:
                try:
                    sizes = video_sizes(full)
                    filetype = 'video'
                except Exception, e:
                    pass
            if not filetype:
                continue

            namebase, ext = os.path.splitext(fn)
            count = 0
            while 1:
                if count:
                    title = ''.join([namebase, '_'+str(count), ext])
                else:
                    title = fn
                slug = slugify(title)
                try:
                    p = GalleryItemBase.objects.get(title_slug=slug)
                except GalleryItemBase.DoesNotExist:
                    if filetype == 'image':
                        item = Photo(title=title,
                                  title_slug=slug)
                    elif filetype == 'video':
                        item = Video(title=title,
                                  title_slug=slug)
                    else:
                        raise Exception("Unknown file type")

                    file_root = os.path.join(settings.MEDIA_ROOT, get_storage_path(item, ''))
                    prefix = os.path.commonprefix([file_root , full])
                    url = full[len(prefix):]

                    item.file.storage.__class__ = OverrideStorage
                    item.file.save(url, TemporaryFile(open(full, 'rb')), save=False)
                    item.save()
                    if abs(item.date_taken - item.date_added) < timedelta(seconds=3):
                        item.date_taken = date_taken
                        item.save()
                    break
                count = count + 1
