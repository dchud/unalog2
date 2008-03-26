from django.contrib.auth.models import User, Group
from django.db import models as m


class GroupProfile (m.Model):
    group = m.OneToOneField(Group, related_name='profile')
    desc = m.TextField(blank=True)
    is_private = m.BooleanField(default=False, db_index=True)
    stoken = m.CharField(blank=True, max_length=32, default='')
    date_created = m.DateTimeField(auto_now_add=True)
    date_modified = m.DateTimeField(auto_now=True)
    # NOTE: Am removing the notion of a group admin by choice
        
    class Admin:
        list_display = ['group', 'desc', 'is_private', 'date_created']
        list_filter = ['is_private', 'date_created']
        ordering = ['group']
        search_fields = ['desc']
        
    class Meta:
        ordering = ['group']
        

class UserProfile (m.Model):
    user = m.ForeignKey(User, unique=True)
    is_private = m.BooleanField(default=False, db_index=True)
    default_to_private_entry = m.BooleanField(default=False)
    url = m.URLField(blank=True, verify_exists=True)
    token = m.CharField(blank=True, max_length=32)
    tz = m.CharField(blank=True, max_length=6)
    group_invites = m.ManyToManyField(Group, related_name='invitees')
    date_modified = m.DateTimeField(auto_now=True)

    class Admin:
        list_display = ['user', 'url', 'is_private', 
            'default_to_private_entry']
        list_filter = ['is_private', 'default_to_private_entry']
        ordering = ['user']
        search_fields = ['url']
        

class Filter (m.Model):
    user = m.ForeignKey(User, related_name='filters')
    attr_name = m.CharField(max_length=20)
    value = m.CharField(max_length=50)
    is_exact = m.BooleanField(default=False)
    is_active = m.BooleanField(default=True)
    
    class Admin:
        list_display = ['id', 'user', 'attr_name', 'value', 
            'is_exact', 'is_active']
        list_filter = ['attr_name', 'is_exact', 'is_active']
        ordering = ['user', 'attr_name', 'value']
        search_fields = ['value']


class Tag (m.Model):
    name = m.CharField(max_length=50, unique=True)
    
    def __unicode__ (self):
        return self.name
        
    class Admin:
        list_display = ['id', 'name']


class Entry (m.Model):
    ENTRY_TYPE_CHOICES = [
        ('l', 'Web link'),
        ]
        
    # Default to 'web link' just to save a step
    etype = m.CharField(max_length=1, choices=ENTRY_TYPE_CHOICES,
        default=ENTRY_TYPE_CHOICES[0][0])
    user = m.ForeignKey(User, related_name='entries')
    title = m.CharField(max_length=255)
    url = m.URLField(blank=True, db_index=True)
    comment = m.TextField(blank=True)
    is_private = m.BooleanField(default=False, db_index=True)
    content = m.TextField(blank=True)
    tags = m.ManyToManyField(Tag, related_name='entries')
    groups = m.ManyToManyField(Group, related_name='entries')
    date_created = m.DateTimeField(auto_now_add=True)
    date_modified = m.DateTimeField(auto_now=True)
    
    def __unicode__ (self):
        return '<Entry: %s (%s)>' % (self.id, self.user.username)
        
    class Admin:
        list_display = ['id', 'user', 'etype', 'url', 'date_created']
        list_filter = ['date_created']
        search_fields = ['title', 'url']
