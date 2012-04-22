from django.core.management.base import BaseCommand, CommandError
from photologue.models import MediaSize, MediaModel

class Command(BaseCommand):
    help = ('Clears the Photologue cache for the given sizes.')
    args = '[sizes]'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **kwargs):
        return clear_cache(args)

def clear_cache(sizes):
    """
    Clears the cache for the given sizes
    """
    size_list = [size.strip(' ,') for size in sizes]

    if len(size_list) < 1:
        sizes = MediaSize.objects.all()
    else:
        sizes = MediaSize.objects.filter(name__in=size_list)

    if not len(sizes):
        raise CommandError('No photo sizes were found.')

    print 'Flushing cache...'

    for cls in MediaModel.__subclasses__():
        print cls.__name__
        for mediasize in sizes:
            print 'Flushing %s size images' % mediasize.name
            for obj in cls.objects.all():
                obj.remove_size(mediasize)
