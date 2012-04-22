import os
from datetime import timedelta
from cStringIO import StringIO
from django.core.files.temp import NamedTemporaryFile
from django.core.files.base import ContentFile, File
from django.utils.timezone import make_aware, get_current_timezone
from django.template.defaultfilters import slugify
from photologue.utils.video import video_sizes
from photologue.utils.libmc import get_moi_details, set_mpg_dar
from photologue.models import Photo, Video, GalleryItemBase

try:
    import Image
except ImportError:
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")

# content is file content or file object
def upload_file(name, original_name, content, date_taken=None, retrieve_another=None,
                tags=None, gallery=None, caption=None, is_public=None, count=0):
    # NOTE: This is workaround to posponed dar update
    # We cannot change provided content,
    # it can be a read-only reference
    update_dar = False

    if original_name.startswith('__'): # do not process meta files
        return count
    if type(content) == str and not len(content):
        return count

    filetype = False
    # Is it an image?
    try:
        # the following is taken from django.newforms.fields.ImageField:
        #  load() is the only method that can spot a truncated JPEG,
        #  but it cannot be called sanely after verify()
        if type(content) == str:
            inp = StringIO(content)
        else:
            inp = content
        trial_image = Image.open(inp)
        trial_image.load()
        # Start reading the file from beginning
        inp.seek(0)
        # verify() is the only method that can spot a corrupt PNG,
        #  but it must be called immediately after the constructor
        trial_image = Image.open(inp)
        trial_image.verify()
        # Ok, It is an image
        filetype = 'image'
    except Exception, e:
        # if a "bad" file is found we just leave it.
        pass
    # Is it a video?
    if not filetype:
        try:
            if type(content) == str:
                inp = NamedTemporaryFile()
                inp.write(content)
            else:
                inp = content
            # Try to open this file as video and get sizes
            sizes = video_sizes(inp.name)
            # Ok, it is a video
            filetype = 'video'

            # Check for special camera files
            if original_name.lower().endswith(".mod") and retrieve_another:
                # Translate D -> I and d -> i
                moi_file = original_name[:-1] + chr(ord(original_name[-1]) + 5)
                # This may fail, but it is OK, we will just upload original MOD file
                moi_data = retrieve_another(moi_file)
                details = get_moi_details(moi_data)
                date_taken = make_aware(details['datetime'], get_current_timezone())
                if name == original_name:
                    name = "MOV-%s.MPG" % date_taken.strftime("%Y%m%d-%H%M%S")
                else:
                    namebase, ext = os.path.splitext(name)
                    name = ''.join([namebase, '.MPG'])
                # NOTE: default mpg aspect ratio is 4:3
                #       change aspect ratio if source is widescreen 16:9 
                if details["video_format"] > 1:
                    update_dar = True
        except Exception, e:
            # if a "bad" file is found we just leave it.
            pass
    if not filetype:
        return count

    name = os.path.basename(name)
    namebase, ext = os.path.splitext(name)
    while 1:
        if count:
            title = ''.join([namebase, '_'+str(count), ext])
        else:
            title = name
        slug = slugify(title)
        try:
            p = GalleryItemBase.objects.get(title_slug=slug)
        except GalleryItemBase.DoesNotExist:
            kwargs = {
                'title': title,
                'title_slug': slug,
                }
            if caption:
                kwargs['caption'] = caption
            if is_public:
                kwargs['is_public'] = is_public

            if filetype == 'image':
                item = Photo(**kwargs)
            elif filetype == 'video':
                item = Video(**kwargs)
            else:
                raise Exception("Unknown file type")
            if type(content) == str:
                item.file.save(name, ContentFile(content), save=False)
            else:
                item.file.save(name, File(content), save=False)
            item.save()
            if tags:
                item.tags.add(*tags)
            # Assume that item is added to photologue at least 3 seconds after created
            if date_taken and abs(item.date_taken - item.date_added) < timedelta(seconds=3):
                item.date_taken = date_taken
                item.save()
            if gallery:
                gallery.items.add(item)
            if update_dar:
                try:
                    set_mpg_dar(item.file.path)
                except:
                    pass
            break
        count = count + 1
    return count
