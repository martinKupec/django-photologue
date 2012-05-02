""" Newforms Admin configuration for Photologue

"""
import os
from datetime import timedelta
from django import forms
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from models import *
from admin_tweaks.actions import slow_delete_selected

class SlowDeleteModelAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        actions = super(SlowDeleteModelAdmin, self).get_actions(request)
        d = actions['delete_selected']
        actions['delete_selected'] = (slow_delete_selected, d[1], d[2])
        return actions

class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_added', 'item_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'title_slug': ('title',)}
    search_fields = ['items']
    filter_horizontal = ('items',)

class GalleryItemModelAdmin(SlowDeleteModelAdmin):
    actions = ['reconvert']

    def add_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'add_exclude', ())
        return super(GalleryItemModelAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'edit_exclude', ())
        return super(GalleryItemModelAdmin, self).change_view(*args, **kwargs)

    def reconvert(self, request, changelist):
        for item in changelist:
            item.clear_cache()
            item.pre_cache()
        self.message_user(request, _("Items scheduled to reconvert."))
    reconvert.short_description = _("Reconvert")

class PhotoOverrideInline(generic.GenericTabularInline):
    model = MediaOverride
    verbose_name = _("photo override")
    verbose_name_plural = _("photo overrides")
    exclude = ('date_taken',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mediasize":
            db_field.verbose_name = _("ImageSize")
            ids = ImageSize.objects.all()
            kwargs["queryset"] = MediaSize.objects.filter(id__in=ids)
        return super(PhotoOverrideInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class PhotoAdmin(GalleryItemModelAdmin):
    inlines = [PhotoOverrideInline]
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 50
    prepopulated_fields = {'title_slug': ('title',)}
    add_exclude = ('date_taken', )
    edit_exclude = ()

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = _('Tags')

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'file':
            db_field.verbose_name = _('Photo')
        return super(PhotoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

class VideoOverrideInline(generic.GenericTabularInline):
    model = MediaOverride
    verbose_name = _("video override")
    verbose_name_plural = _("video overrides")
    exclude = ('date_taken',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mediasize":
            db_field.verbose_name = _("VideoSize")
            ids = VideoSize.objects.all()
            kwargs["queryset"] = MediaSize.objects.filter(id__in=ids)
        return super(VideoOverrideInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class VideoAdmin(GalleryItemModelAdmin):
    inlines = [VideoOverrideInline]
    list_display = ('title', 'date_taken', 'date_added', 'duration', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 50
    prepopulated_fields = {'title_slug': ('title',)}
    add_exclude = ('crop_from', 'date_taken')
    edit_exclude = ('crop_from', )

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = _('Tags')

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'file':
            db_field.verbose_name = _('Video')
        return super(VideoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

class VideoConvertAdmin(admin.ModelAdmin):
    list_display = ('video', 'videosize', 'status', 'the_time', 'access_date')
    list_filter = ['videosize', 'converted']
    exclude = ('time',)
    search_fields = ['video']
    list_per_page = 100
    list_max_show_all = 600

    def the_time(self, convert):
        return str(timedelta(seconds=convert.time))
    the_time.short_description = _('Convertion time')

    def status(self, convert):
        if not convert.converted and not convert.inprogress:
            return _("Queued") 
        path = convert.video._get_SIZE_filename(convert.videosize.name, invalid_ok=True)
        try:
            s = os.stat(path)
            fsize = s.st_size
        except OSError, e:
            fsize = 0
        if convert.converted:
            status = "<img src=\"/static/admin/img/icon-yes.gif\" alt=\"True\" /> "
            status += _("Done") + ""
        else:
            status = _("In progress")
        return status + " (%0.2fM)" % (fsize/(1024*1024.))
    status.short_description = _('Status')
    status.allow_tags = True

class GalleryPermissionAdmin(admin.ModelAdmin):
    list_display = ('gallery', 'can_access_gallery', 'can_see_normal_size', 'can_download_full_size', 'can_download_zip',)
    list_filter = ['can_access_gallery', 'can_see_normal_size', 'can_download_full_size', 'can_download_zip']
    search_fields = ['gallery', 'users']
    filter_horizontal = ('users',)

class ImageEffectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color', 'brightness', 'contrast', 'sharpness', 'filters', 'admin_sample')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Adjustments', {
            'fields': ('color', 'brightness', 'contrast', 'sharpness')
        }),
        ('Filters', {
            'fields': ('filters',)
        }),
        ('Reflection', {
            'fields': ('reflection_size', 'reflection_strength', 'background_color')
        }),
        ('Transpose', {
            'fields': ('transpose_method',)
        }),
    )

class ImageSizeAdmin(SlowDeleteModelAdmin):
    list_display = ('name', 'width', 'height', 'crop', 'pre_cache', 'effect', 'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height', 'quality')
        }),
        ('Options', {
            'fields': ('upscale', 'crop', 'pre_cache', 'increment_count')
        }),
        ('Enhancements', {
            'fields': ('effect', 'watermark',)
        }),
    )

class VideoSizeAdmin(SlowDeleteModelAdmin):
    list_display = ('name', 'videotype', 'width', 'height', 'videobitrate', 'audiobitrate', 'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height', 'videotype')
        }),
        ('Options', {
            'fields': ('twopass', 'upscale', 'crop', 'letterbox', 'increment_count')
        }),
        ('Quality', {
            'fields': ('videobitrate', 'audiobitrate',)
        }),
    )

class WatermarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'opacity', 'style')


class GalleryUploadAdminForm(forms.ModelForm):
    class Meta:
        model = GalleryUpload
    def clean_title(self):
        title = self.cleaned_data['title']
        gallery = self.cleaned_data['gallery']
        if not title and not gallery:
            raise forms.ValidationError(_("Eighter gallery or title has to be filled."))
        return self.cleaned_data["title"]

class GalleryUploadAdmin(admin.ModelAdmin):
    form = GalleryUploadAdminForm
    def has_change_permission(self, request, obj=None):
        return False # To remove the 'Save and continue editing' button

admin.site.register(Gallery, GalleryAdmin)
admin.site.register(GalleryUpload, GalleryUploadAdmin)
admin.site.register(GalleryPermission, GalleryPermissionAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(ImageEffect, ImageEffectAdmin)
admin.site.register(ImageSize, ImageSizeAdmin)
admin.site.register(Watermark, WatermarkAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(VideoSize, VideoSizeAdmin)
admin.site.register(VideoConvert, VideoConvertAdmin)
