import sys, os, subprocess, re, shlex, string
from base64 import b64decode
from tempfile import mktemp
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
#from photologue.models import VideoConvert

FFMPEG = getattr(settings, 'VIDEOLOGUE_FFMPEG', 'ffmpeg')
FLVTOOL = getattr(settings, 'VIDEOLOGUE_FLVTOOL', 'flvtool2')
AUDIO_CODEC = getattr(settings, 'VIDEOLOGUE_AUDIO_CODEC', 'libmp3lame')
AUDIO_SAMPLING_RATE = getattr(settings, 'VIDEOLOGUE_AUDIO_SAMPLING_RATE', 22050)

hq_pre = '''\
coder=1
flags=+loop
cmp=+chroma
partitions=-parti8x8-parti4x4-partp8x8-partb8x8
me_method=umh
subq=8
me_range=16
g=250
keyint_min=25
sc_threshold=40
i_qfactor=0.71
b_strategy=2
qcomp=0.6
qmin=10
qmax=51
qdiff=4
bf=4
refs=4
directpred=3
trellis=1
flags2=+bpyramid+wpred+mixed_refs+dct8x8+fastpskip
'''

ipod640_pre = '''\
coder=0
bf=0
refs=1
flags2=-wpred-dct8x8
level=30
maxrate=10000000
bufsize=10000000
'''

def video_sizes(video_file):
    indata = subprocess.Popen([FFMPEG, '-i', video_file],
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    indata = '\n'.join(indata.communicate())

    # Get input width, height, and SAR&DAR, for anamorphic video
    try:
        w, h, sar_n, sar_d, dar_n, dar_d = \
            [int(_) for _ in
            re.search("Video: .* (\d+)x(\d+)[, ].*SAR (\d+):(\d+) DAR (\d+):(\d+)",
                indata, re.I).groups()]
    except:
        raise Exception(indata)
    # Calculate real width
    w = w*sar_n/sar_d
    # Aspect ratio
    aspect = 1.*dar_n/dar_d
    return (w, h, aspect)

def execute(command, header):
    print header
    print "Command: %s\n" % command

    child = subprocess.Popen(shlex.split(str(command)), stdout=subprocess.PIPE)

    msg = header + "\n"
    msg += "Command: %s\n" % command
    msg += reduce(lambda i, s: i + s + "\n", child.stdout.readlines(), "")
    msg += "Returncode: %d" % (child.returncode if child.returncode else 0)

    return (msg, child.returncode)

def video_create_poster(videopath, poster, video_data):
    ''' Grab a PNG snapshot of the video
    '''

    output = ""
    w,h,aspect = video_sizes(videopath)
    thumbnailfile = NamedTemporaryFile(suffix='.png')
    grabimage = (   '%(ffmpeg)s -y -i "%(infile)s" '
                    '-vframes 1 -ss 00:00:10 -an '
                    '-vcodec png -f rawvideo '
                    '-s %(size)s %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG,
                        infile=videopath,
                        outfile=thumbnailfile.name,
                        size="%dx%d" % (w, h)
                    )

    (message, retval) = execute(grabimage, "-------------------- GRAB IMAGE ------------------")
    output += message
    if retval:
        raise Exception('Creating poster have failed\n\n' + output)

    # Replace part after last dot by 'png'
    name = os.path.basename(videopath)
    dot = name.rfind('.')
    if dot != -1:
        name = name[:dot]
    name = name+'.png'
    # Save
    poster.file.save(name, File(thumbnailfile))
    poster.save()
    return output

def convertvideo_flv(video_in, video_out, videosize, video_data):
    ''' Convert the video to .flv
    '''

    output = ""
    bitrate = "%s" % videosize.audiobitrate

    ffmpeg = (  '%(ffmpeg)s -y -i "%(infile)s" '
                '-acodec %(audioc)s -ar %(audiosr)s -ab %(audiobr)s '
                '-f flv %(letterboxing)s -s %(size)s %(outfile)s'
                ) % dict(
                    ffmpeg=FFMPEG,
                    infile=video_in,
                    audioc=AUDIO_CODEC,
                    audiosr=AUDIO_SAMPLING_RATE,
                    audiobr=bitrate,
                    letterboxing=video_data.get('letterboxing', ''),
                    size=video_data['size'],
                    outfile=video_out
                )

    if FLVTOOL:
        flvtool = "%s -U %s" % (FLVTOOL, video_out)

    output += "Source : %s\n" % video_in
    output += "Target : %s\n" % video_out

    (message, retval) = execute(ffmpeg, "------------------ FFMPEG : FLV ----------------")
    output += message
    if retval:
        raise Exception('FLV creation have failed(ffmpeg)\n\n' + output)

    if FLVTOOL:
        (message, retval) = execute(flvtool, "-------------------- FFLVTOOL ------------------")
        output += message
        if retval:
            raise Exception('FLV creation have failed(flvtool)\n\n' + output)

    s = os.stat(video_out)
    fsize = s.st_size
    if (fsize == 0):
        output += "Target file is 0 bytes conversion failed?\n"
        raise Exception('FLV creation have failed(file zero size)\n\n' + output)
    return output

def convertvideo_mp4(video_in, video_out, videosize, video_data):
    ''' Convert the video to .mp4
    '''

    output = ""
    try:
        hq_prefilename = mktemp()
        hq_prefile = open(hq_prefilename, 'w')
        hq_prefile.write(hq_pre)
        hq_prefile.close()
        ipod640_prefilename = mktemp()
        ipod640_prefile = open(ipod640_prefilename, 'w')
        ipod640_prefile.write(ipod640_pre)
        ipod640_prefile.close()

        bitrate = "%dk" % videosize.videobitrate
    
        if videosize.twopass:
            original_files = os.listdir('.') # used later for cleanup
            ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" -b:v %(bitrate)s '
                        '-vcodec libx264 -fpre "%(hq_prefile)s" -fpre "%(ipod640_prefile)s" '
                        '-an -pass 1 -s %(size)s %(letterboxing)s -f rawvideo '
                        '%(outfile)s'
                        ) % dict(
                            ffmpeg=FFMPEG,
                            source=video_in,
                            size=video_data['size'],
                            letterboxing=video_data.get('letterboxing', ''),
                            # For first-pass, use a null output.  Windows needs the
                            #   NUL keyword, linuxy systems can use /dev/null
                            outfile='/dev/null' if os.path.exists('/dev/null') else 'NUL',
                            ipod640_prefile=ipod640_prefilename,
                            hq_prefile=hq_prefilename,
                            bitrate=bitrate,
                        )
    
            output += "Source : %s\n" % video_in
            output += "Target : %s\n" % video_out
    
            (message, retval) = execute(ffmpeg, "------------- FFMPEG : MP4 : Pass1 -------------")
            output += message
            if retval:
                raise Exception('MP4 creation have failed(pass 1)\n\n' + output)
    
        ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" -b:v %(bitrate)s '
                    '-vcodec libx264 -fpre "%(hq_prefile)s" -fpre "%(ipod640_prefile)s" '
                    '-acodec libfaac -ac 2 '
                    '%(letterboxing)s '
                    '-s %(size)s %(twopass)s %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG, source=video_in,
                        letterboxing=video_data.get('letterboxing', ''),
                        size=video_data['size'],
                        twopass='-pass 2' if videosize.twopass else '',
                        outfile=video_out,
                        ipod640_prefile=ipod640_prefilename,
                        hq_prefile=hq_prefilename,
                        bitrate=bitrate,
                    )
    
        output += "Source : %s\n" % video_in
        output += "Target : %s\n" % video_out
    
        header = ("------------- FFMPEG : MP4 : Pass2 -------------" if videosize.twopass else
                  "----------------- FFMPEG : MP4 -----------------")
        (message, retval) = execute(ffmpeg, header)
        output += message
        if retval:
            raise Exception('MP4 creation have failed(final pass)\n\n' + output)
    
        s = os.stat(video_out)
        fsize = s.st_size
        if (fsize == 0):
            output += "Target file is 0 bytes conversion failed?\n\n"
            raise Exception('MP4 creation have failed(file zero size)\n\n' + output)
    finally:
        if videosize.twopass:
            # Cleanup our 2-pass logfiles
            logs = filter(lambda x: x.endswith('.log') and '2pass' in x, set(os.listdir('.'))-set(original_files))
            for log in logs:
                os.unlink(log)
    
        os.unlink(hq_prefilename)
        os.unlink(ipod640_prefilename)
    return output

def convertvideo_ogv(video_in, video_out, videosize, video_data):
    ''' Convert the video to .ogv
    '''

    output = ""
    bitrate = "%dk" % videosize.videobitrate
    ffmpeg = (  '%(ffmpeg)s -y -i "%(infile)s" -b:v %(bitrate)s '
                '-vcodec libtheora -acodec libvorbis '
                '%(letterboxing)s -s %(size)s %(outfile)s '
                ) % dict(
                    ffmpeg=FFMPEG,
                    infile=video_in,
                    letterboxing=video_data.get('letterboxing', ''),
                    size=video_data['size'],
                    outfile=video_out,
                    bitrate=bitrate,
                )

    output += "Source : %s\n" % video_in
    output += "Target : %s\n" % video_out

    (message, retval) = execute(ffmpeg, "------------------ FFMPEG : OGV ----------------")
    output += message
    if retval:
        raise Exception('OGV creation have failed\n\n' + output)

    s = os.stat(video_out)
    fsize = s.st_size
    if (fsize == 0):
        output += "Target file is 0 bytes conversion failed?\n"
        raise Exception('OGV creation have failed(file zero size)\n\n' + output)
    return output

def convertvideo_webm(video_in, video_out, videosize, video_data):
    ''' Convert the video to .webm
    '''

    libvpx_flags = ('-qcomp 0.6 -g 360 -qmin 0 -qmax 60 -quality best '
                    '-vp8flags +altref -rc_lookahead 16 '
                    '-minrate 20 -maxrate 800 '
                    '-mb_threshold 0 -skip_threshold 0 '
                    )

    output = ""
    try:
        bitrate = "%dk" % videosize.videobitrate
    
        if videosize.twopass:
            original_files = os.listdir('.') # used later for cleanup
            ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" -b:v %(bitrate)s '
                        '-vcodec libvpx -slices 2 %(vpxflags)s '
                        '-an -pass 1 -s %(size)s %(letterboxing)s -f rawvideo '
                        '%(outfile)s'
                        ) % dict(
                            ffmpeg=FFMPEG,
                            source=video_in,
                            size=video_data['size'],
                            letterboxing=video_data.get('letterboxing', ''),
                            # For first-pass, use a null output.  Windows needs the
                            #   NUL keyword, linuxy systems can use /dev/null
                            outfile='/dev/null' if os.path.exists('/dev/null') else 'NUL',
                            vpxflags=libvpx_flags,
                            bitrate=bitrate,
                        )
    
            output += "Source : %s\n" % video_in
            output += "Target : %s\n" % video_out
    
            (message, retval) = execute(ffmpeg, "------------- FFMPEG : WEBM : Pass1 -------------")
            output += message
            if retval:
                raise Exception('WEBM creation have failed(pass 1)\n\n' + output)
    
        ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" -b:v %(bitrate)s '
                    '-vcodec libvpx -slices 2 %(vpxflags)s '
                    '-acodec libvorbis -ac 2 '
                    '%(letterboxing)s '
                    '-s %(size)s %(twopass)s %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG, source=video_in,
                        letterboxing=video_data.get('letterboxing', ''),
                        size=video_data['size'],
                        twopass='-pass 2' if videosize.twopass else '',
                        outfile=video_out,
                        vpxflags=libvpx_flags,
                        bitrate=bitrate,
                    )
    
        output += "Source : %s\n" % video_in
        output += "Target : %s\n" % video_out
    
        header = ("------------- FFMPEG : WEBM : Pass2 -------------" if videosize.twopass else
                  "----------------- FFMPEG : WEBM -----------------")
        (message, retval) = execute(ffmpeg, header)
        output += message
        if retval:
            raise Exception('WEBM creation have failed(final pass)\n\n' + output)
    
        s = os.stat(video_out)
        fsize = s.st_size
        if (fsize == 0):
            output += "Target file is 0 bytes conversion failed?\n"
            raise Exception('WEBM creation have failed(file zero size)\n\n' + output)
    
    finally:
        if videosize.twopass:
            # Cleanup our 2-pass logfiles
            logs = filter(lambda x: x.endswith('.log') and '2pass' in x, set(os.listdir('.'))-set(original_files))
            for log in logs:
                os.unlink(log)
    return output
