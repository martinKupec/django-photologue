import os
import shutil
from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from photologue.default_settings import *
from photologue.models import Video
from photologue.utils.hashdb import *
from photologue.utils.snippets import unique_strvalue

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--symlink', '-s', action="store_true", dest='symlink', default=False,
            help='Symlink imported files instead of copying'),
        )
    help = 'Import content of selected folder to photologue.'
    args = 'folder'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args) < 1:
            return 'Need a folder to work on.\n'
        return import_videos(args[0], options.get('symlink')) + '\n'

fncache = os.path.join(settings.MEDIA_ROOT, get_storage_path(None, ".hash_cache"))
fndeleted = os.path.join(settings.MEDIA_ROOT, get_storage_path(None, ".hash_deleted"))

def hash_videos():
    db = {}
    names = set()
    hash_cache = {}
    
    try:
        fcache = open(fncache, 'r')
        for line in fcache:
            hash, atime, path = line.split(' ', 2)
            path = path[:-1]
            hash_cache[path] = (hash, float(atime))
        fcache.close()
    except IOError, e:
        if e.errno != 2:
            raise e

    for video in Video.objects.values_list('file', flat=True):
        if video in names:
            print "Duplicate video entry: %s" % video
            continue
        names.add(video)
        path = os.path.join(settings.MEDIA_ROOT, video)
        if not os.path.exists(path):
            print "File does not exist: ", path
            continue

        # Try cache
        if path in hash_cache and abs(os.path.getatime(path) - hash_cache[path][1]) < 0.0001:
            hash = hash_cache[path][0]
        else:
            hash = get_hash(path)
            update_db(hash, path)

        if hash in db:
            print "Duplicate file: %s - %s" % (path, db[hash])
            continue
        db[hash] = path
    save_db(db)
    return (db, names)

def save_db(db):
    fcache = open(fncache, 'w')
    for key, value in db.items():
        atime = os.path.getatime(value)
        fcache.write("%(hash)s %(atime)f %(file)s\n" % dict(hash=key, file=value, atime=atime))
    fcache.close()

def update_db(hash, path):
    fcache = open(fncache, 'a')
    atime = os.path.getatime(path)
    fcache.write("%(hash)s %(atime)f %(file)s\n" % dict(hash=hash, file=path, atime=atime))
    fcache.close()

def file_copy(s, t, symlink=False):
    if os.path.exists(t):
        raise Exception("Target file exists: %s" % t)
    if symlink:
        try:
            os.symlink(s, t)
        except Exception, e:
            raise Exception("Unable to copy %s: %s" % (s, e))
    else:
        try:
            shutil.copy2(s, t)
        except Exception, e:
            raise Exception("Unable to copy %s: %s" % (s, e))


def import_videos(folder, symlink=False):
    """
    Import content of the folder to photologue.
    """

    if not os.path.isdir(folder):
        return "Provided folder is not a valid folder."

    db,names = hash_videos()

    deleted = {}
    try:
        fdeleted = open(fndeleted, 'r')
        for line in fdeleted:
            hash, path = line.split(' ', 2)
            path = path[:-1]
            deleted[hash] = path
        fdeleted.close()
    except IOError, e:
        if e.errno != 2:
            raise e

    for video in os.listdir(folder):
        path = os.path.join(folder, video)
        ext = video.split('.')[-1].lower()
        if not ext in PHOTOLOGUE_VIDEO_EXTENTIONS:
            print "Non video file found: ", path
            continue
        hash = get_hash(path)
        if hash in db:
            print "File already imported: ", path
            continue

        if hash in deleted:
            print "File previously deleted: ", path, " - ", deleted[hash]
            continue

        item = Video()
        queryset = Video.objects.all()
        unique_strvalue(item, video, 'title', queryset, ' ')
        unique_strvalue(item, video, 'title_slug', queryset, slug=True)
        target = get_storage_path(item, video)
        if target in names:
            print "File already targeted: ", path
        dest = os.path.join(settings.MEDIA_ROOT, target)
        try:
            file_copy(path, dest, symlink)
        except Exception, e:
            print e
            continue
        item.file = target
        item.save()
        db[hash] = dest
        update_db(hash, dest)
        names.add(target)
        print "Imported", target, hash
    save_db(db)
    return "OK"
