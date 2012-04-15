""" Newforms Admin configuration for Photologue

"""
from django.contrib import admin
from django.contrib.contenttypes import generic
from models import *

try:
    from batchadmin.admin import BatchModelAdmin
except ImportError:
    BatchModelAdmin = admin.ModelAdmin

class GalleryAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    list_display = ('title', 'date_added', 'item_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'title_slug': ('title',)}
    search_fields = ['items']
    filter_horizontal = ('items',)

class PhotoOverrideInline(generic.GenericTabularInline):
    model = MediaOverride
    verbose_name = "photo override"
    verbose_name_plural = "photo overrides"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mediasize":
            db_field.verbose_name = "ImageSize"
            ids = ImageSize.objects.all()
            kwargs["queryset"] = MediaSize.objects.filter(id__in=ids)
        return super(PhotoOverrideInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class PhotoAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    inlines = [PhotoOverrideInline]
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'title_slug': ('title',)}

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = 'Tags'

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'file':
            db_field.verbose_name = 'Photo'
        return super(PhotoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

class VideoOverrideInline(generic.GenericTabularInline):
    model = MediaOverride
    verbose_name = "video override"
    verbose_name_plural = "video overrides"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mediasize":
            db_field.verbose_name = "VideoSize"
            ids = VideoSize.objects.all()
            kwargs["queryset"] = MediaSize.objects.filter(id__in=ids)
        return super(VideoOverrideInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class VideoAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    inlines = [VideoOverrideInline]
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'title_slug': ('title',)}
    exclude = ('poster', 'flv_video', 'mp4_video', 'ogv_video', 'webm_video', 'crop_from')

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = 'Tags'

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'file':
            db_field.verbose_name = 'Video'
        return super(VideoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

class GalleryPermissionAdmin(BatchModelAdmin):
    list_display = ('gallery', 'can_access_gallery', 'can_see_normal_size', 'can_download_full_size', 'can_download_zip',)
    list_filter = ['can_access_gallery', 'can_see_normal_size', 'can_download_full_size', 'can_download_zip']
    search_fields = ['gallery', 'users']
    filter_horizontal = ('users',)

class ImageEffectAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
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

class ImageSizeAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
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

class VideoSizeAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    list_display = ('name', 'width', 'height', 'crop', 'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height')
        }),
        ('Options', {
            'fields': ('upscale', 'crop', 'increment_count')
        }),
        #('Enhancements', {
        #    'fields': ('effect', 'watermark',)
        #}),
    )

class WatermarkAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    list_display = ('name', 'opacity', 'style')


class GalleryUploadAdmin(BatchModelAdmin):
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
