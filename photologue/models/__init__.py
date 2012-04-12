
def slugify(title):
    downcode = Downcoder().downcode
    return django.template.defaultfilters.slugify(downcode(title))

from media import *
from gallery import *
from image import *
from photo import *
from video import *

from django.db.models.signals import post_init

# Set up the accessor methods
def add_methods(sender, instance, signal, *args, **kwargs):
    """ Adds methods to access sized images (urls, paths)

    after the Photo model's __init__ function completes,
    this method calls "add_accessor_methods" on each instance.
    """
    if hasattr(instance, 'add_accessor_methods'):
        instance.add_accessor_methods()
# connect the add_accessor_methods function to the post_init signal
post_init.connect(add_methods)
