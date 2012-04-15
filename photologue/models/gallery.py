from datetime import datetime
from os import path

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from photologue.default_settings import *
from taggit.managers import TaggableManager

from media import MediaModel


class Gallery(models.Model):
    date_added = models.DateTimeField(_('date published'), default=datetime.now)
    title = models.CharField(_('title'), max_length=100, unique=True)
    title_slug = models.SlugField(_('title slug'), unique=True,
                                  help_text=_('A "slug" is a unique URL-friendly title for an object.'))
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    items = models.ManyToManyField('GalleryItemBase', related_name='galleries', verbose_name=_('items'),
                                    null=True, blank=True)#, through="GalleryMedia")
    tags = TaggableManager(blank=True)

    class Meta:
        ordering = ['-date_added']
        get_latest_by = 'date_added'
        verbose_name = _('gallery')
        verbose_name_plural = _('galleries')

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.__unicode__()

    def get_absolute_url(self):
        return reverse('pl-gallery', args=[self.title_slug])

    def latest(self, limit=LATEST_LIMIT, public=True):
        return self.items.latest(limit, public)

    def sample(self, count=0, public=True):
        return self.items.sample(count, public)

    def cover(self):
        try:
            return self.items.filter(is_thumbnail=True).all()[0]
        except:
            return self.items.all()[0]

    def item_count(self, public=True):
        return self.items.item_count(public)
    item_count.short_description = _('count')
    
    def latest_item(self, public=True):
        try:
            if public:
                return self.latest(limit=1)[0]
            else:
                return self.latest(limit=1)[0]
        except IndexError:
            return False

    def public(self):
        return self.items.public()

    def first_zip(self):
        try:
            return self.galleryupload_set.all()[0]
        except:
            return None

#class GalleryMedia(models.Model):
#    gallery = models.ForeignKey(Gallery)
#    media = models.ForeignKey(MediaModel)

class GalleryPermission(models.Model):
    gallery = models.ForeignKey(Gallery, null=True, blank=True, help_text=_('Select a gallery to set the users and permissions for.'))
    users = models.ManyToManyField(User, related_name='my_galleries', verbose_name=_('Has Gallery Access'),
                                    null=True, blank=True)

    can_access_gallery = models.BooleanField(_('can view thumbnails'), default=True, help_text=_('Uncheck this to prevent the users from seeing the gallery.'))
    can_see_normal_size = models.BooleanField(_('can browse gallery'), default=True, help_text=_('Uncheck to prevent users from seeing gallery in detail.'))
    can_download_full_size = models.BooleanField(_('can download media'), default=True, help_text=_('Uncheck this to prevent users from downloading media.'))
    can_download_zip = models.BooleanField(_('can download zip files of the whole gallery'), default=True, help_text=_('Uncheck this to prevent users from downloading a zip file of the whole gallery.'))


class GalleryUpload(models.Model):
    zip_file = models.FileField(_('media file zip'), upload_to=path.join(PHOTOLOGUE_DIR, "zip-uploads"),
                                help_text=_('Select a .zip file of images to upload into a new Gallery.'))
    gallery = models.ForeignKey(Gallery, null=True, blank=True, help_text=_('Select a gallery to add these images to. leave this empty to create a new gallery from the supplied title.'))
    title = models.CharField(_('title'), max_length=75, help_text=_('All items in the gallery will be given a title made up of the gallery title + a sequential number.'))
    caption = models.TextField(_('caption'), blank=True, help_text=_('Caption will be added to all items.'))
    description = models.TextField(_('description'), blank=True, help_text=_('A description of this Gallery.'))
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Uncheck this to make the uploaded gallery and included media private.'))
    tags = TaggableManager(blank=True)

    class Meta:
        verbose_name = _('gallery upload')
        verbose_name_plural = _('gallery uploads')

    def save(self, *args, **kwargs):
        super(GalleryUpload, self).save(*args, **kwargs)
        gallery = self.process_zipfile()
        #FIXME - next line added from video
        super(GalleryUpload, self).delete()
        return gallery

    def process_zipfile(self):
        if path.isfile(self.zip_file.path):
            try:
                zip = zipfile.ZipFile(self.zip_file.path)
                bad_file = zip.testzip()
            except:
                bad_file = self.zip_file.path
            if bad_file:
                raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)

            count = 1
            if self.gallery:
                gallery = self.gallery
            else:
                gallery = Gallery.objects.create(title=self.title,
                                                 title_slug=slugify(self.title),
                                                 description=self.description,
                                                 is_public=self.is_public,
                                                 tags=self.tags)
            from cStringIO import StringIO
            for filename in sorted(zip.namelist()):
                if filename.startswith('__'): # do not process meta files
                    continue
                data = zip.read(filename)
                if len(data):
                    good = False
                    # Is it an image?
                    try:
                        # the following is taken from django.newforms.fields.ImageField:
                        #  load() is the only method that can spot a truncated JPEG,
                        #  but it cannot be called sanely after verify()
                        trial_image = Image.open(StringIO(data))
                        trial_image.load()
                        # verify() is the only method that can spot a corrupt PNG,
                        #  but it must be called immediately after the constructor
                        trial_image = Image.open(StringIO(data))
                        trial_image.verify()
                        # Ok, It is an image
                        good = True
                    except Exception:
                        # if a "bad" file is found we just leave it.
                        pass
                    # Is it a video?
                    if not good:
                        try:
                            #FIXME need test for video file

                            # Ok, It is an image
                            good = True
                        except Exception:
                            # if a "bad" file is found we just leave it.
                            pass
                    if not good: 
                        continue
                    while 1:
                        title = ' '.join([self.title, str(count)])
                        slug = slugify(title)
                        try:
                            p = Media.objects.get(title_slug=slug)
                        except Media.DoesNotExist:
                            item = Media(title=title,
                                          title_slug=slug,
                                          caption=self.caption,
                                          is_public=self.is_public,
                                          tags=self.tags)
                            item.path.save(filename, ContentFile(data))
                            #FIXME next line is not checked
                            GalleryPhoto.objects.create(gallery=gallery, photo=photo)
#                            gallery.photos.add(photo)
                            #FROM VIDEOLOGUE
                            video.original_video.save(filename, ContentFile(data), save=False)
                            video.save()
                            gallery.videos.add(video)
                            #END FROM VIDEOLOGUE
                            count = count + 1
                            break
                        count = count + 1
            zip.close()
            return gallery

class GalleryItemQuerySet(models.query.QuerySet):
    def iterator(self):
        iter = super(GalleryItemQuerySet, self).iterator()
        for obj in iter:
            subclass = False
            for cls in GalleryItemBase.__subclasses__():
                cls = cls.__name__.lower()
                if hasattr(obj, cls):
                    subclass = True
                    yield getattr(obj, cls)
                    break
            if not subclass:
                yield obj

class GalleryItemManager(models.Manager):
    def get_query_set(self):
        return GalleryItemQuerySet(self.model)

    def latest(self, limit=LATEST_LIMIT, public=True):
        if public:
            item_set = self.public()
        else:
            item_set = self.all()
        if limit == 0:
            return item_set
        return item_set[:limit]

    def item_count(self, is_public=True):
        if is_public:
            return self.public().count()
        else:
            return self.count()

    def public(self):
        return self.filter(is_public=True)

    def sample(self, count=0, public=True):
        if public:
            item_set = self.public().order_by('?')
        else:
            item_set = self.order_by('?')
        if count == 0:
            return item_set
        return item_set[:count]

class GalleryItemBase(models.Model):
    title = models.CharField(_('title'), max_length=100, unique=True)
    title_slug = models.SlugField(_('slug'), unique=True,
                                  help_text=('A "slug" is a unique URL-friendly title for an object.'))
    caption = models.TextField(_('caption'), blank=True)
    date_added = models.DateTimeField(_('date added'), default=datetime.now, editable=False)
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Public photographs will be displayed in the default views.'))
    is_thumbnail = models.BooleanField(_('Is the main thumbnail for the gallery'), default=False, help_text=_('This image will show up as the thumbnail for the gallery.'))

    tags = TaggableManager(blank=True)
    objects = GalleryItemManager()

    class Meta:
        ordering = ['-date_added']
        get_latest_by = 'date_added'

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        if self.title_slug is None:
            self.title_slug = slugify(self.title)
        super(GalleryItemBase, self).save(*args, **kwargs)

    def type(self):
        for cls in GalleryItemBase.__subclasses__():
            cls = cls.__name__.lower()
            if hasattr(self, cls):
                return cls
        return type(self).__name__.lower()

    def get_absolute_url(self):
        return reverse('pl-'+self.type(), args=[self.title_slug])

    def public_galleries(self):
        """Return the public galleries to which this item belongs."""
        return self.galleries.filter(is_public=True)

    def get_previous_in_gallery(self, gallery):
        try:
            return self.get_previous_by_date_added(galleries__exact=gallery,
                                                   is_public=True)
        except GalleryItemBase.DoesNotExist:
            return None

    def get_next_in_gallery(self, gallery):
        try:
            return self.get_next_by_date_added(galleries__exact=gallery,
                                               is_public=True)
        except GalleryItemBase.DoesNotExist:
            return None
