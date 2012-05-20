import os
from optparse import make_option
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from photologue.models import VideoConvert, poster_unconverted, MediaSizeCache, Video
from photologue.utils.video import *
from photologue.default_settings import *

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--poster-only', '-p', action="store_true", dest='poster_only', default=False,
            help='Convert only posters, but check all videos.'),
        make_option('--unlock', '-u', action="store_true", dest='unlock', default=False,
            help='Remove any "in progress" marks before converting'),
        )
    help = 'Converts unprocessed photologue video files.'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        cleanup_converts()
        if options.get('unlock'):
            unlock_converts()
        if options.get('poster_only'):
            return process_posters()
        return process_files()

def should_convert_poster(video):
    if poster_unconverted(video.poster):
        return True
    if not os.path.exists(video.poster.file.path):
        return True
    for size in MediaSizeCache().sizes.values():
        related_model = type(size).__name__.split('.')[-1].lower().replace('size', 'model')
        if related_model == 'videomodel':
            path = getattr(video, 'get_%s_filename' % size)()
            if os.path.exists(path):
                return False
    return True

def process_posters():
    for video in Video.objects.all():
        try:
            if video.poster and should_convert_poster(video):
                video_data = {
                              'orig_w': video.width,
                              'orig_h': video.height,
                              'duration': video.duration,
                             }
                print video_create_poster(video.file.path, video.poster, video_data)
        except Exception, e:
            print e

def process_files():
    """
    Creates videosize files for the given video objects.
    """

    convert_videos = VideoConvert.objects.filter(converted=False, inprogress=False)

    if not convert_videos:
        print "No videos to convert"

    for convert in convert_videos:
        # Reload
        convert = VideoConvert.objects.get(id=convert.id)
        if convert.inprogress or convert.converted:
            continue
        # We are processing it - lock
        # This is not 100% coherent lock, but it should do
        convert.inprogress = True
        convert.message = ''
        convert.save()

        filepath = convert.video.file.path
        # Calculate size to convert
        try:
            out_w, out_h = video_calculate_size(convert.video, convert.videosize)
        except Exception, e:
            print "Failed to get sizes: ", os.path.split(filepath)[1]
            convert.message = e
            convert.inprogress = False
            convert.save()
            continue

        video_data = {
                      'orig_w': convert.video.width,
                      'orig_h': convert.video.height,
                      'duration': convert.video.duration,
                      'size': (out_w, out_h),
                      'videobitrate': convert.videosize.videobitrate,
                      'audiobitrate': convert.videosize.audiobitrate,
                      'twopass': convert.videosize.twopass,
                      }
        if convert.videosize.letterbox:
            video_data['letterboxing'] = '-vf pad="%d:%d:(ow-iw)/2:(oh-ih)/2:black"' % (out_w, out_h)

        # Create poster
        try:
            if convert.video.poster and should_convert_poster(convert.video):
                convert.message = video_create_poster(filepath, convert.video.poster, video_data)
        except Exception, e:
            print e
            convert.inprogress = False
            convert.message = e
            convert.save()
            continue

        func = 'convertvideo_%s' % convert.videosize.videotype
        start = datetime.now()
        try:
            out = convert.video._get_SIZE_filename(convert.videosize.name, invalid_ok=True)
            try:
                os.remove(out)
            except:
                pass
            convert.message += globals()[func](filepath, out, video_data)
        except Exception, e:
            try:
                os.remove(out)
            except:
                pass
            print e
            convert.inprogress = False
            convert.message = e
            convert.save()
            continue
        convert.time = (datetime.now() - start).total_seconds()
        convert.inprogress = False
        convert.converted = True
        convert.save()

def cleanup_converts():
    for convert in VideoConvert.objects.all():
        if not convert.converted:
            continue
        # Delete all older than 7 days
        if (now() - convert.access_date) > timedelta(7):
            convert.delete()

def unlock_converts():
    for convert in VideoConvert.objects.all():
        if convert.inprogress:
            convert.inprogress = False
            convert.save()
