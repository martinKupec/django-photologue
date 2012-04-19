from photologue.models import ImageSize
from photologue.models import VideoSize, VIDEO_TYPES

def get_response(msg, func=int, default=None):
    while True:
        resp = raw_input(msg + ' ')
        if not resp and default is not None:
            return default
        try:
            return func(resp)
        except:
            print 'Invalid input.'

def create_imagesize(name, width=0, height=0, upscale=False, crop=False, pre_cache=False, increment_count=False):
    try:
        size = ImageSize.objects.get(name=name)
        exists = True
    except ImageSize.DoesNotExist:
        size = ImageSize(name=name)
        exists = False
    if exists:
        msg = 'A "%s" image size already exists. Do you want to replace it? (yes, no):' % name
        if not get_response(msg, lambda inp: inp == 'yes', False):
            return
    print '\nWe will now define the "%s" image size:\n' % size
    w = get_response('Width (in pixels):', lambda inp: int(inp), width)
    h = get_response('Height (in pixels):', lambda inp: int(inp), height)
    u = get_response('Upscale media? (yes, no):', lambda inp: inp == 'yes', upscale)
    c = get_response('Crop to fit? (yes, no):', lambda inp: inp == 'yes', crop)
    p = get_response('Pre-cache? (yes, no):', lambda inp: inp == 'yes', pre_cache)
    i = get_response('Increment count? (yes, no):', lambda inp: inp == 'yes', increment_count)
    size.width = w
    size.height = h
    size.upscale = u
    size.crop = c
    size.pre_cache = p
    size.increment_count = i
    size.save()
    print '\nA "%s" image size has been created.\n' % name
    return size

def create_videosize(name, width=0, height=0, videotype=None, twopass=True, upscale=False,
            crop=False, letterbox=True, increment_count=False, videobitrate=2000, audiobitrate=32000):
    try:
        size = VideoSize.objects.get(name=name)
        exists = True
    except VideoSize.DoesNotExist:
        size = VideoSize(name=name)
        exists = False
    if exists:
        msg = 'A "%s" video size already exists. Do you want to replace it? (yes, no):' % name
        if not get_response(msg, lambda inp: inp == 'yes', False):
            return
    print '\nWe will now define the "%s" video size:\n' % size
    print "Available choices for video type are:"
    i = 1
    msg = ""
    for type in VIDEO_TYPES:
        msg += "\t " + str(i) + " - " + type[1] + "\n"
        i += 1
    msg += 'Select Video type:'
    def type_test(inp):
        n = int(inp) - 1
        if n >= len(VIDEO_TYPES):
            raise
        return n
    t = get_response(msg, type_test, videotype)
    w = get_response('Width (in pixels):', default=width)
    h = get_response('Height (in pixels):', default=height)
    tp= get_response('Two pass? (yes, no):', lambda inp: inp == 'yes', twopass)
    u = get_response('Upscale media? (yes, no):', lambda inp: inp == 'yes', upscale)
    c = get_response('Crop to fit? (yes, no):', lambda inp: inp == 'yes', crop)
    l = get_response('Letterbox? (yes, no):', lambda inp: inp == 'yes', letterbox)
    i = get_response('Increment count? (yes, no):', lambda inp: inp == 'yes', increment_count)
    vb= get_response('Video bitrate (in kbps):', default=videobitrate)
    ab= get_response('Audio bitrate (in bps, 0 - mute):',  default=audiobitrate)
    size.width = w
    size.height = h
    size.videotype = VIDEO_TYPES[t][0]
    size.twopass = tp
    size.upscale = u
    size.crop = c
    size.letterbox = l
    size.increment_count = i
    size.videobitrate = vb
    size.audiobirate = ab
    size.save()
    print '\nA "%s" video size has been created.\n' % name
    return size
