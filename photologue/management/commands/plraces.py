import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, is_aware, make_aware, get_current_timezone
from django.template.defaultfilters import slugify

from photologue.models import Video, Event, Race
from photologue.default_settings import *

class Command(BaseCommand):
    help = _('Scan videos and update races')

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return refresh_races()

def refresh_races():
    """
    Scan videos and update races
    """

    events = Event.objects.all()
    videos = Video.objects.exclude(id__in=Race.objects.values('video'))

    for video in videos:
        event = events.filter(day_start__lte=video.date_taken, day_end__gte=video.date_taken)
        if not event:
            print "Video %s not in any event (%s)!" % (video.title, video.date_taken)
            continue
        if len(event) > 1:
            print "More than one event for video %s: " % video.title,
            for e in event:
                print e.venue, " ",
            print " - adding to first listed"
        # Take the event
        event = event[0]
        race = Race(video=video, event=event)
        try:
            race.save()
        except Exception, e:
            print e
            continue
        print "Added %s to %s" % (video.title, event.title)
