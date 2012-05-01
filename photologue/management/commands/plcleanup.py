import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.move import file_move_safe

from photologue.default_settings import *
from photologue.utils.hashdb import *
from photologue.models import Race

PHOTOLOGUE_ARCHIVE = getattr(settings, 'PHOTOLOGUE_ARCHIVE', os.path.join(settings.MEDIA_ROOT, 'archive'))
PHOTOLOGUE_ERASE_NAME = getattr(settings, 'PHOTOLOGUE_ERASE_NAME', 'ERASE')
PHOTOLOGUE_PRIVATE_NAME = getattr(settings, 'PHOTOLOGUE_PRIVATE_NAME', 'PRIVATE')

class Command(BaseCommand):
    help = 'Sort out special races.'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return cleanup_races()

def cleanup_videos(queue):
    erasedb   = readdb(os.path.join(PHOTOLOGUE_ARCHIVE, '.erasedb') )
    privatedb = readdb(os.path.join(PHOTOLOGUE_ARCHIVE, '.privatedb') )

    private_folder = os.path.join(PHOTOLOGUE_ARCHIVE, 'private')

    if not os.path.isdir(PHOTOLOGUE_ARCHIVE):
        os.makedirs(PHOTOLOGUE_ARCHIVE)
    if not os.path.isdir(private_folder):
        os.makedirs(private_folder)

    for video, how in queue:
        if not os.path.exists(video.file.path):
            print video, " file missing: ", video.file.path
            continue
        hash = get_hash(video.file.path)
        filename = os.path.basename(video.file.url)
        if hash in erasedb:
            print "File ", filename ," already erased: ", erasedb[hash]
            continue
        if hash in privatedb:
            print "File ", filename," already moved to private: ", privatedb[hash]
            continue
        if how == 'erase':
            try:
                os.remove(video.file.path)
                erasedb[hash] = filename
                print "File ", filename, " erased ", hash
            except:
                print "Unable to erase ", video.file.path
                continue
        elif how == 'private':
            try:
                target = os.path.join(private_folder, filename)
                # Work around django bug
                if os.path.exists(target):
                    raise IOError("target file exists")
                file_move_safe(video.file.path, target, allow_overwrite=False)
                privatedb[hash] = filename
                print "File ", filename, " moved to private ", hash
            except Exception, e:
                print "Unable to move ", video.file.path, " ", e
                continue
        else:
            raise Exception("Unknown action type: %s" % how)
        video.delete()
    writedb(os.path.join(PHOTOLOGUE_ARCHIVE, '.erasedb'), erasedb )
    writedb(os.path.join(PHOTOLOGUE_ARCHIVE, '.privatedb'), privatedb )

def cleanup_races():
    """
    Erase "ERASE" riders, move "PRIVATE" riders
    """
    queue = []
    for race in Race.objects.all():
        if not race.rider:
            continue
        if race.rider.name == PHOTOLOGUE_ERASE_NAME:
            queue.append((race.video, 'erase'))
        elif race.rider.name == PHOTOLOGUE_PRIVATE_NAME:
            queue.append((race.video, 'private'))
    cleanup_videos(queue)
