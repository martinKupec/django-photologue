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
    list_display = ('title', 'date_added', 'media_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'title_slug': ('title',)}
    search_fields = ['media']
    filter_horizontal = ('media',)

class PhotoAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'title_slug': ('title',)}

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = 'Tags'

class VideoAdmin(BatchModelAdmin):
    batch_actions = ['delete_selected']
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'the_tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'title_slug': ('title',)}
    exclude = ('poster', 'flv_video', 'mp4_video', 'ogv_video', 'webm_video', 'crop_from')

    def the_tags(self, obj):
        return ", ".join(map(lambda x: x.name, obj.tags.all()))
    the_tags.short_description = 'Tags'

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

class MediaOverrideInline(generic.GenericTabularInline):
    model = MediaOverride

admin.site.register(Gallery, GalleryAdmin)
admin.site.register(GalleryUpload, GalleryUploadAdmin)
admin.site.register(GalleryPermission, GalleryPermissionAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(ImageEffect, ImageEffectAdmin)
admin.site.register(ImageSize, ImageSizeAdmin)
admin.site.register(Watermark, WatermarkAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(VideoSize, VideoSizeAdmin)
