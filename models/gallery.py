from os import path
from datetime import datetime
import zipfile
import unicodedata

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now, make_aware, get_current_timezone
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

from photologue.default_settings import *
from taggit.managers import TaggableManager
from taggit.utils import parse_tags

from media import MediaModel


class Gallery(models.Model):
    date_added = models.DateTimeField(_('date published'), default=now)
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
        app_label=THIS_APP
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
            return self.latest(limit=1, public=public)[0]
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

    class Meta:
        app_label=THIS_APP


class GalleryUpload(models.Model):
    zip_file = models.FileField(_('media file zip'), upload_to=path.join(PHOTOLOGUE_DIR, "zip-uploads"),
                                help_text=_('Select a .zip file of images to upload into a new Gallery.'))
    gallery = models.ForeignKey(Gallery, null=True, blank=True, help_text=_('Select a gallery to add these images to. leave this empty to create a new gallery from the supplied title.'))
    title = models.CharField(_('title'), max_length=75, help_text=_('Title of the new gallery.'), blank=True, null=True)
    use_title = models.BooleanField(_('use title'), default=False, help_text=_('If checked, uploaded files will be named by title + sequencial number'))
    caption = models.TextField(_('caption'), blank=True, help_text=_('Caption will be added to all items.'))
    description = models.TextField(_('description'), blank=True, help_text=_('A description of this Gallery.'))
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Uncheck this to make the uploaded gallery and included media private.'))
    tags = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        app_label=THIS_APP
        verbose_name = _('gallery upload')
        verbose_name_plural = _('gallery uploads')

    def save(self, *args, **kwargs):
        super(GalleryUpload, self).save(*args, **kwargs)
        try:
            self.process_zipfile()
            os.remove(self.zip_file.path)
            super(GalleryUpload, self).delete()
        except Exception, e:
            pass

    def process_zipfile(self):
        from photologue.utils.upload import upload_file
        if path.isfile(self.zip_file.path):
            try:
                zip = zipfile.ZipFile(self.zip_file.path)
                bad_file = zip.testzip()
            except:
                bad_file = self.zip_file.path
            if bad_file:
                raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)

            parsed_tags = parse_tags(self.tags)
            if self.gallery:
                gallery = self.gallery
                self.title = gallery.title
            else:
                gallery = Gallery.objects.create(title=self.title,
                                                 title_slug=slugify(self.title),
                                                 description=self.description,
                                                 is_public=self.is_public)
                gallery.save()
            gallery.tags.add(*parsed_tags)
            count = 0

            def read_file(fn):
                try:
                    return zip.read(fn)
                except:
                    return None

            for filename in sorted(zip.namelist()):
                data = zip.read(filename)
                file_mtime = zip.getinfo(filename).date_time
                file_mtime = make_aware(datetime(*file_mtime), get_current_timezone())
                if self.use_title:
                    name = os.path.basename(filename)
                    namebase, ext = os.path.splitext(name)
                    name = ''.join([self.title, ext])
                else:
                    name = filename
                count = upload_file(name, filename, data, file_mtime, read_file, parsed_tags, gallery, self.caption, self.is_public, count)
                if not self.use_title:
                    count = 0
            zip.close()

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
    # Fixing mult-table inheritance field shadowing
    gallery_id = models.AutoField(db_column='id', primary_key=True)

    title = models.CharField(_('title'), max_length=100, unique=True)
    title_slug = models.SlugField(_('slug'), unique=True,
                                  help_text=('A "slug" is a unique URL-friendly title for an object.'))
    caption = models.TextField(_('caption'), blank=True)
    date_added = models.DateTimeField(_('date added'), default=now, editable=False)
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Public photographs will be displayed in the default views.'))
    is_thumbnail = models.BooleanField(_('Is the main thumbnail for the gallery'), default=False, help_text=_('This image will show up as the thumbnail for the gallery.'))

    tags = TaggableManager(blank=True)
    objects = GalleryItemManager()

    class Meta:
        app_label=THIS_APP
        ordering = ['-date_added']
        get_latest_by = 'date_added'

    def __unicode__(self):
        return self.title

    def __str__(self):
        return unicodedata.normalize('NFKD', self.__unicode__()).encode('ascii', 'ignore')

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

            return self.galleryitembase_ptr.get_previous_by_date_added(
                        galleries__exact=gallery, is_public=True)
        except GalleryItemBase.DoesNotExist:
            return None

    def get_next_in_gallery(self, gallery):
        try:
            return self.galleryitembase_ptr.get_next_by_date_added(
                        galleries__exact=gallery, is_public=True)
        except GalleryItemBase.DoesNotExist:
            return None
