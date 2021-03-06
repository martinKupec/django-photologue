import os
import stat
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

# This is the name of this application set to Meta app_label to all models
# this is needed in order to work with 'splitted models'
THIS_APP = 'photologue'

# Default limit for gallery.latest
LATEST_LIMIT = getattr(settings, 'PHOTOLOGUE_GALLERY_LATEST_LIMIT', None)

# max_length setting for the ImageModel ImageField
MEDIA_FIELD_MAX_LENGTH = getattr(settings, 'PHOTOLOGUE_MEDIA_FIELD_MAX_LENGTH', 100)

# Path to sample image
SAMPLE_IMAGE_PATH = getattr(settings, 'SAMPLE_IMAGE_PATH', os.path.join('res', 'sample.jpg'))

# Modify image file buffer size.
MAXBLOCK = getattr(settings, 'PHOTOLOGUE_MAXBLOCK', 256 * 2 ** 10)

# Photologue media path relative to media root
PHOTOLOGUE_DIR = getattr(settings, 'PHOTOLOGUE_DIR', 'photologue')

# Should we delete files without a database entry?
PHOTOLOGUE_REMOVE_DELETED = getattr(settings, 'PHOTOLOGUE_REMOVE_DELETED', True)

# Look for user function to define file paths
PHOTOLOGUE_PATH = getattr(settings, 'PHOTOLOGUE_PATH', None)
if PHOTOLOGUE_PATH is not None:
    if callable(PHOTOLOGUE_PATH):
        get_storage_path = PHOTOLOGUE_PATH
    else:
        parts = PHOTOLOGUE_PATH.split('.')
        module_name = '.'.join(parts[:-1])
        module = import_module(module_name)
        get_storage_path = getattr(module, parts[-1])
else:
    def get_storage_path(instance, filename):
        return os.path.join(PHOTOLOGUE_DIR, 'media', filename)

# Path to default video poster
DEFAULT_POSTER_PATH = getattr(settings, 'POSTER_PATH', os.path.join('res', 'sample.jpg'))

# Should we delete files without a database entry?
PHOTOLOGUE_POSTER_TIME = getattr(settings, 'PHOTOLOGUE_POSTER_TIME', '00:00:03.0')

# Make all file creations user/group rw
DEFAULT_PHOTOLOGUE_GROUP_WRITE = getattr(settings, 'PHOTOLOGUE_GROUP_WRITE', True)
if DEFAULT_PHOTOLOGUE_GROUP_WRITE:
    old = os.umask(stat.S_IWOTH)

PHOTOLOGUE_VIDEO_EXTENTIONS = getattr(settings, 'PHOTOLOGUE_VIDEO_EXTENTIONS', ['mpg', 'mov'])

# Quality options for JPEG images
JPEG_QUALITY_CHOICES = (
    (30, _('Very Low')),
    (40, _('Low')),
    (50, _('Medium-Low')),
    (60, _('Medium')),
    (70, _('Medium-High')),
    (80, _('High')),
    (90, _('Very High')),
)

# choices for new crop_anchor field in Photo
CROP_ANCHOR_CHOICES = (
    ('top', _('Top')),
    ('right', _('Right')),
    ('bottom', _('Bottom')),
    ('left', _('Left')),
    ('center', _('Center (Default)')),
)

IMAGE_TRANSPOSE_CHOICES = (
    ('FLIP_LEFT_RIGHT', _('Flip left to right')),
    ('FLIP_TOP_BOTTOM', _('Flip top to bottom')),
    ('ROTATE_90', _('Rotate 90 degrees counter-clockwise')),
    ('ROTATE_270', _('Rotate 90 degrees clockwise')),
    ('ROTATE_180', _('Rotate 180 degrees')),
)

WATERMARK_STYLE_CHOICES = (
    ('tile', _('Tile')),
    ('scale', _('Scale')),
)
