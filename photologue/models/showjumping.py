from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from photologue.default_settings import *
from photologue.utils.snippets import unique_strvalue
from taggit.managers import TaggableManager
from video import Video

class GalleryImposter(models.Model):
    class Meta:
        abstract = True
        app_label=THIS_APP

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.__unicode__()

    def type(self):
        for cls in GalleryImposter.__subclasses__():
            cls = cls.__name__.lower()
            if hasattr(self, cls):
                return cls
        return type(self).__name__.lower()

    def get_absolute_url(self):
        return reverse('pl-' + self.type(), args=[self.title_slug])

    def latest(self, limit=LATEST_LIMIT, public=True):
        if public:
            item_set = self.public()
        else:
            item_set = self.items
        if limit == 0:
            return item_set
        return item_set[:limit]

    def sample(self, count=0, public=True):
        if public:
            items = self.public()
        else:
            items = self.items
        if count == 0:
            return items
        else:
            return items[:count]

    def cover(self):
        try:
            return self.items.filter(is_thumbnail=True)[0]
        except:
            return self.items[0]

    def item_count(self, public=True):
        if public:
            return self.public().count()
        else:
            return self.items.count()
    item_count.short_description = _('count')

    def latest_item(self, public=True):
        try:
            return self.latest(limit=1, public=public)[0]
        except IndexError:
            return False

    def public(self):
        return self.items.filter(is_public=True)

class RaceGalleryImposter(GalleryImposter):
    @property
    def items(self):
        video_ids = self.race_set.values_list('video_id', flat=True)
        return Video.objects.filter(id__in=video_ids)

    class Meta:
        abstract = True
        app_label=THIS_APP

class Horse(RaceGalleryImposter):
    name = models.CharField(_('name'), max_length=100, unique=True)
    nick = models.SlugField(_('Nickname'), help_text=_('Horse nickname for archivation.'), unique=True)
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    tags = TaggableManager(blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    @property
    def title(self):
        return self.name

    @property
    def title_slug(self):
        return self.nick

    class Meta:
        app_label=THIS_APP
        verbose_name = _('horse')
        verbose_name_plural = _('horses')

class Rider(RaceGalleryImposter):
    name = models.CharField(_('name'), max_length=100, unique=True)
    nick = models.SlugField(_('Nickname'), help_text=_('Riders nickname for archivation.'), unique=True)
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    tags = TaggableManager(blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    @property
    def title(self):
        return self.name

    @property
    def title_slug(self):
        return self.nick

    class Meta:
        app_label=THIS_APP
        verbose_name = _('rider')
        verbose_name_plural = _('riders')

class Venue(GalleryImposter):
    venue = models.CharField(_('venue'), max_length=100, unique=True)
    venue_slug = models.SlugField(_('venue slug'), unique=True,
                                  help_text=_('A "slug" is a unique URL-friendly title for an object.'))
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    tags = TaggableManager(blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    @property
    def items(self):
        return self.event_set

    @property
    def title(self):
        return self.venue

    @property
    def title_slug(self):
        return self.venue_slug

    class Meta:
        app_label=THIS_APP
        verbose_name = _('venue')
        verbose_name_plural = _('venues')

class Event(RaceGalleryImposter):
    name = models.CharField(_('name'), max_length=100)
    name_slug = models.CharField(_('name slug'), max_length=100)
    venue = models.ForeignKey(Venue, verbose_name=_('venue'), null=False, blank=False)
    day_start = models.DateField(_('first day'))
    day_end = models.DateField(_('last day'))

    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    tags = TaggableManager(blank=True)

    def get_absolute_url(self):
        return reverse('pl-event', args=[self.name_slug])

    @property
    def title(self):
        return self.name + ", " + self.venue.title

    @property
    def title_slug(self):
        return self.name_slug + "__" + self.venue.title_slug

    class Meta:
        app_label=THIS_APP
        unique_together = (('venue', 'day_start'), )
        verbose_name = _('event')
        verbose_name_plural = _('events')

class JumpingLevel(models.Model):
    level = models.CharField(_('obstacles level'), max_length=20)
    jumpoff = models.BooleanField(_('jumpoff'), default=False)

    def __unicode__(self):
        return self.level + (u' - %s' % _('jumpoff') if self.jumpoff else u'')

    def __str__(self):
        return self.__unicode__()

    @property
    def slug(self):
        out = self.level.replace('*', '_')
        if self.jumpoff:
            out += "-jumpoff"
        print out
        return out

    class Meta:
        app_label=THIS_APP
        unique_together = (('level', 'jumpoff'),)
        verbose_name = _('jumping level')
        verbose_name_plural = _('jumping levels')

class Race(models.Model):
    video = models.OneToOneField(Video, verbose_name=_('video'), null=False, blank=False, unique=True)
    rider = models.ForeignKey(Rider, verbose_name=_('rider'), null=True, blank=False)
    horse = models.ForeignKey(Horse, verbose_name=_('horse'), null=True, blank=False)
    level = models.ForeignKey(JumpingLevel, verbose_name=_('course level'), null=True, blank=False)
    event = models.ForeignKey(Event, verbose_name=_('event'), null=True, blank=False)

    class Meta:
        app_label=THIS_APP
        verbose_name = _('race')
        verbose_name_plural = _('races')

    def save(self, *args, **kwargs):
        super(Race, self).save(*args, **kwargs)

        if self.video and self.rider and self.horse and self.level:
            title = "%(horse)s - %(rider)s - %(level)s" % dict(
                        horse=self.horse,
                        rider=self.rider,
                        level=self.level,
                    )
            title_slug = "%(horse)s - %(rider)s - %(level)s" % dict(
                        horse=self.horse.nick,
                        rider=self.rider.nick,
                        level=self.level.slug,
                    )
            queryset = Video.objects.all()
            unique_strvalue(self.video, title, 'title', queryset)
            unique_strvalue(self.video, title_slug, 'title_slug', queryset, slug=True)
            self.video.save()
