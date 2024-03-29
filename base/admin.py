from django.contrib import admin

from base import models as m

class GroupProfileAdmin(admin.ModelAdmin):
    list_display = ['group', 'desc', 'is_private', 'date_created']
    list_filter = ['is_private', 'date_created']
    ordering = ['group']
    search_fields = ['desc']
    
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'url', 'is_private', 
        'default_to_private_entry', 'date_modified']
    list_filter = ['is_private', 'default_to_private_entry']
    ordering = ['user']
    search_fields = ['url']
        
class FilterAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'attr_name', 'value', 
        'is_exact', 'is_active']
    list_filter = ['attr_name', 'is_exact', 'is_active']
    ordering = ['user', 'attr_name', 'value']
    search_fields = ['value']

class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    
class UrlAdmin(admin.ModelAdmin):
    list_display = ['id', 'value']
    search_fields = ['value']
    
class EntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'is_private', 'date_created']
    list_filter = ['date_created', 'is_private']
    search_fields = ['id', 'title']

class EntryTagAdmin(admin.ModelAdmin):
    list_display = ['id', 'entry', 'tag', 'sequence_num']
    search_fields = ['tag']

admin.site.register(m.GroupProfile, GroupProfileAdmin)
admin.site.register(m.UserProfile, UserProfileAdmin)
admin.site.register(m.Filter, FilterAdmin)
admin.site.register(m.Tag, TagAdmin)
admin.site.register(m.Url, UrlAdmin)
admin.site.register(m.Entry, EntryAdmin)
admin.site.register(m.EntryTag, EntryTagAdmin)
