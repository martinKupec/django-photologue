from django.core.management.base import BaseCommand, CommandError
from photologue.management.commands import create_imagesize, create_videosize

class Command(BaseCommand):
    help = ('Creates a new Photologue size interactively.')
    requires_model_validation = True
    can_import_settings = True

    args = 'size_type size_name'

    def handle(self, *args, **options):
        if len(args) < 2:
            print "Needs size type and size name"
            print "Size types are:\n\tphoto\n\tvideo"
            return
        if args[0] == 'photo':
            create_imagesize(args[1])
        elif args[0] == 'video':
            create_videosize(args[1])
        else:
            print "Unknown size type"
            print "Size types are:\n\tphoto\n\tvideo"
