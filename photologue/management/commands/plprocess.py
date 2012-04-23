import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from photologue.models import VideoConvert, poster_unconverted
from photologue.utils.video import *
from photologue.default_settings import *

class Command(BaseCommand):

    help = ('Converts unprocessed photologue video files.')

    args = ['[poster]']
    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return process_files(*args)

def process_files(select=None):
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
        # Get input sizes
        try:
            in_w, in_h, in_aspect = video_sizes(filepath)
        except Exception, e:
            print "Failed to get sizes: ", os.path.split(filepath)[1]
            convert.message = e
            convert.inprogress = False
            convert.save()
            continue

        # Get output sizes
        out_w = convert.videosize.width
        out_h = convert.videosize.height
        if out_w == out_h == 0:
            out_w = in_w
            out_h = in_h
        elif out_w == 0:
            out_w = int((out_h*in_aspect + 1)/2)*2
        elif out_h == 0:
            out_h = int((out_w/in_aspect + 1)/2)*2
        
        video_data = {'size': (out_w, out_h),
                      'videobitrate': convert.videosize.videobitrate,
                      'audiobitrate': convert.videosize.audiobitrate,
                      'twopass': convert.videosize.twopass,
                      }
        if convert.videosize.letterbox:
            # Desired output aspect
            out_aspect = 1.*out_w/out_h
            # Calculate the needed height
            conv_height = int(out_w/in_aspect)
            # Set for processing
            video_data['letterboxing'] = '-vf pad="%d:%d:(ow-iw)/2:(oh-ih)/2:black"' % (out_w, conv_height)
            video_data['size'] = (out_w, conv_height)

        # Create poster
        try:
            if convert.video.poster and poster_unconverted(convert.video.poster):
                convert.message = video_create_poster(filepath, convert.video.poster, video_data)
        except Exception, e:
            print e
            convert.inprogress = False
            convert.message = e
            convert.save()
            continue


        if select == 'poster':
            # Save after poster creation
            convert.inprogress = False
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
