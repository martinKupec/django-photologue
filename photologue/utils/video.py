import sys, os, subprocess, re, shlex, string
from base64 import b64decode
from tempfile import mktemp
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from photologue.default_settings import *

FFMPEG = getattr(settings, 'PHOTOLOGUE_FFMPEG', 'ffmpeg')
QTFAST = getattr(settings, 'PHOTOLOGUE_QTFAST', 'qt-faststart')
FLVTOOL = getattr(settings, 'PHOTOLOGUE_FLVTOOL', 'flvtool2')
#AUDIO_AAC = getattr(settins, 'PHOTOLOGUE_AUDIO_AAC', 'libvo_aacenc')
AUDIO_AAC = getattr(settings, 'PHOTOLOGUE_AUDIO_AAC', 'libfaac -ac 2')
AUDIO_MP3 = getattr(settings, 'PHOTOLOGUE_AUDIO_MP3', 'libmp3lame')
AUDIO_OGG = getattr(settings, 'PHOTOLOGUE_AUDIO_OGG', 'libvorbis')
AUDIO_SAMPLING_RATE = getattr(settings, 'PHOTOLOGUE_AUDIO_SAMPLING_RATE', 22050)

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

    child = subprocess.Popen(shlex.split(str(command)), stdout=subprocess.PIPE, preexec_fn=lambda : os.nice(20))

    msg = header + "\n"
    msg += "Command: %s\n" % command
    msg += reduce(lambda i, s: i + s + "\n", child.stdout.readlines(), "")
    msg += "Returncode: %d\n" % (child.returncode if child.returncode else 0)

    return (msg, child.returncode)

def video_create_poster(videopath, poster, video_data):
    ''' Grab a PNG snapshot of the video
    '''

    output = ""
    w,h,aspect = video_sizes(videopath)
    thumbnailfile = NamedTemporaryFile(suffix='.png')
    grabimage = (   '%(ffmpeg)s -y -i "%(infile)s" '
                    '-vframes 1 -ss %(postertime)s -an '
                    '-vcodec png -f rawvideo '
                    '-s %(size)s %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG,
                        infile=videopath,
                        postertime=PHOTOLOGUE_POSTER_TIME,
                        outfile=thumbnailfile.name,
                        size="%dx%d" % (w, h)
                    )

    (message, retval) = execute(grabimage, "-------------------- GRAB IMAGE ------------------")
    output += message
    if retval:
        raise Exception('Creating poster have failed\n\n' + output)

    s = os.stat(thumbnailfile.name)
    fsize = s.st_size
    if (fsize == 0):
        output += "Target file is 0 bytes conversion failed?\n"
        raise Exception('Poster creation have failed(file zero size)\n\n' + output)

    # Replace part after last dot by 'png'
    name = os.path.basename(videopath)
    dot = name.rfind('.')
    if dot != -1:
        name = name[:dot]
    name = os.path.join("poster", name+'.png')
    # Save
    poster.file.save(name, File(thumbnailfile))

    # Import poster_unconverted here
    from photologue.models.video import poster_unconverted
    if poster_unconverted(poster):
        poster.remove_deleted = False
    poster.save()
    return output

def convertvideo_flv(video_in, video_out, video_data):
    ''' Convert the video to .flv
    '''

    output = ""
    ffmpeg = (  '%(ffmpeg)s -y -i "%(infile)s" '
                '-acodec %(audioc)s -ar %(audiosr)s -ab %(audiobr)s '
                '-f flv %(letterboxing)s -s %(size)s %(outfile)s'
                ) % dict(
                    ffmpeg=FFMPEG,
                    infile=video_in,
                    audioc=AUDIO_CODEC,
                    audiosr=AUDIO_SAMPLING_RATE,
                    audiobr="%s" % video_data['audiobitrate'],
                    letterboxing=video_data.get('letterboxing', ''),
                    size="%dx%d" % video_data['size'],
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

def convertvideo_mp4(video_in, video_out, video_data):
    ''' Convert the video to .mp4
    '''

    output = ""
    try:
        common_options = ('-vcodec libx264 -vprofile high -preset slower -b:v %(vb)dk '
                          '-maxrate %(vb)dk -bufsize %(bfs)dk %(letterboxing)s -vf scale=%(size)s '
                          '-threads 0 '
                        ) % dict(
                            vb=video_data['videobitrate'],
                            bfs=2*video_data['videobitrate'],
                            letterboxing=video_data.get('letterboxing', ''),
                            size="%d:%d" % video_data['size'],
                        )
        audio_pass1 = '-an '
        if not video_data['audiobitrate']:
            audio_pass2 = audio_pass1
        else:
            audio_pass2 = ('-acodec %(acodec)s -ar 44100 -b:a %(ab)dk '
                          ) % dict(
                            acodec=AUDIO_AAC,
                            ab=video_data['audiobitrate'],
                            )
    
        if video_data['twopass']:
            original_files = os.listdir('.') # used later for cleanup
            ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" %(common)s '
                        '-pass 1 %(audio)s -f mp4 %(outfile)s'
                        ) % dict(
                            ffmpeg=FFMPEG,
                            source=video_in,
                            common=common_options,
                            audio=audio_pass1,
                            outfile='/dev/null' if os.path.exists('/dev/null') else 'NUL',
                        )
    
            output += "Source : %s\n" % video_in
            output += "Target : %s\n" % video_out
    
            (message, retval) = execute(ffmpeg, "------------- FFMPEG : MP4 : Pass1 -------------")
            output += message
            if retval:
                raise Exception('MP4 creation have failed(pass 1)\n\n' + output)
    
        ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" %(common)s '
                    '%(twopass)s %(audio)s -f mp4 %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG,
                        source=video_in,
                        common=common_options,
                        twopass='-pass 2' if video_data['twopass'] else '',
                        audio=audio_pass2,
                        outfile=video_out,
                    )
    
        output += "Source : %s\n" % video_in
        output += "Target : %s\n" % video_out
    
        header = ("------------- FFMPEG : MP4 : Pass2 -------------" if video_data['twopass'] else
                  "----------------- FFMPEG : MP4 -----------------")
        (message, retval) = execute(ffmpeg, header)
        output += message
        if retval:
            raise Exception('MP4 creation have failed(final pass)\n\n' + output)
    
        # Move moov to start
        tmp = video_out + '_fast'
        qtfast = '%(qtfast)s %(source)s %(tmp)s' % dict(
                        qtfast=QTFAST,
                        source=video_out,
                        tmp=tmp,
                        )
        header = "------------- QT-FASTSTART : MP4  -------------"
        (message, retval) = execute(qtfast, header)
        output += message
        if retval:
            raise Exception('QT-FASTSTART failed\n\n' + output)
        os.rename(tmp, video_out)
        
        s = os.stat(video_out)
        fsize = s.st_size
        if (fsize == 0):
            output += "Target file is 0 bytes conversion failed?\n\n"
            raise Exception('MP4 creation have failed(file zero size)\n\n' + output)
    finally:
        if video_data['twopass']:
            # Cleanup our 2-pass logfiles
            logs = filter(lambda x: x.endswith('.log') and '2pass' in x, set(os.listdir('.'))-set(original_files))
            for log in logs:
                os.unlink(log)
    return output

def convertvideo_ogv(video_in, video_out, video_data):
    ''' Convert the video to .ogv
    '''

    output = ""
    ffmpeg = (  '%(ffmpeg)s -y -i "%(infile)s" -b:v %(bitrate)s '
                '-vcodec libtheora -acodec libvorbis '
                '%(letterboxing)s -s %(size)s %(outfile)s '
                ) % dict(
                    ffmpeg=FFMPEG,
                    infile=video_in,
                    letterboxing=video_data.get('letterboxing', ''),
                    size=video_data['size'],
                    outfile=video_out,
                    bitrate="%dk" % video_data['videobitrate'],
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

def convertvideo_webm(video_in, video_out, video_data):
    ''' Convert the video to .webm
    '''

    output = ""
    try:
        common_options = ('-codec:v libvpx -vpre libvpx-360p -quality good -cpu-used 0 -b:v %(vb)dk -qmin 10 -qmax 42 '
                          '-maxrate %(vb)dk -bufsize %(bfs)dk -threads 2 %(letterboxing)s -vf scale=%(size)s '
                        ) % dict(
                            vb=video_data['videobitrate'],
                            bfs=2*video_data['videobitrate'],
                            letterboxing=video_data.get('letterboxing', ''),
                            size="%d:%d" % video_data['size'],
                        )
        audio_pass1 = '-an '
        if not video_data['audiobitrate']:
            audio_pass2 = audio_pass1
        else:
            audio_pass2 = ('-codec:a %(acodec)s -ar 44100 -b:a %(ab)dk '
                          ) % dict(
                            acodec=AUDIO_OGG,
                            ab=video_data['audiobitrate'],
                            )
    
        if video_data['twopass']:
            original_files = os.listdir('.') # used later for cleanup
            ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" %(common)s '
                        '-pass 1 %(audio)s -f webm %(outfile)s'
                        ) % dict(
                            ffmpeg=FFMPEG,
                            source=video_in,
                            common=common_options,
                            audio=audio_pass1,
                            outfile='/dev/null' if os.path.exists('/dev/null') else 'NUL',
                        )
            output += "Source : %s\n" % video_in
            output += "Target : %s\n" % video_out
    
            (message, retval) = execute(ffmpeg, "------------- FFMPEG : WEBM : Pass1 -------------")
            output += message
            if retval:
                raise Exception('WEBM creation have failed(pass 1)\n\n' + output)
    
        ffmpeg = (  '%(ffmpeg)s -y -i "%(source)s" %(common)s '
                    '%(twopass)s %(audio)s -f webm %(outfile)s'
                    ) % dict(
                        ffmpeg=FFMPEG,
                        source=video_in,
                        common=common_options,
                        twopass='-pass 2' if video_data['twopass'] else '',
                        audio=audio_pass2,
                        outfile=video_out,
                    )
    
        output += "Source : %s\n" % video_in
        output += "Target : %s\n" % video_out
    
        header = ("------------- FFMPEG : WEBM : Pass2 -------------" if video_data['twopass'] else
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
        if video_data['twopass']:
            # Cleanup our 2-pass logfiles
            logs = filter(lambda x: x.endswith('.log') and '2pass' in x, set(os.listdir('.'))-set(original_files))
            for log in logs:
                os.unlink(log)
    return output
