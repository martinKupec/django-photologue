import os
import time
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import get_current_timezone

from photologue.models import Race, Event
from photologue.management.commands.plupdatefiles import update_files
from photologue.management.commands.plcleanup import cleanup_races
from photologue.default_settings import *

class Command(BaseCommand):
    help = 'Move races to archive folder.'
    args = 'destination'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args[0]) < 1:
            return "Need a destination folder - the root for archivation"
        return archivate_files(args[0])

def archivate_files(dest):
    # First do housekeeping
    update_files()
    cleanup_races()
    for event in Event.objects.all():
        folder = "%s-%s-%s" % (event.day_start.strftime('%y%m%d'), event.venue.venue_slug, event.name_slug)
        path = os.path.join(dest, folder)
        try:
            os.mkdir(path)
        except OSError, e:
            #Is it already exist?
            if e.errno != 17:
                print "Cannot create folder %s : %s" % (path, e.strerror)
        for race in Race.objects.filter(event=event):
            if not race.event or not race.rider or not race.horse or not race.level:
               continue

            frm = race.video.file.path
            to = os.path.join(path, os.path.basename(race.video.file.name).lower())

            if os.path.exists(to):
                continue

            if os.path.exists(to):
                continue
            shutil.copy(frm, to)

            taken = race.video.date_taken
            taken = taken.astimezone(get_current_timezone())
            mtime = int(time.mktime(taken.timetuple()))
            os.utime(to, (mtime, mtime))

            os.unlink(frm)
            os.symlink(to, frm)

            print frm, "->", to
