from django.contrib.auth.models import User, Group
from django.db import models as m


class GroupProfile (m.Model):
    group = m.ForeignKey(Group, unique=True, related_name='profile')
    desc = m.TextField(blank=True)
    is_private = m.BooleanField(default=False, db_index=True)
    stoken = m.CharField(blank=True, max_length=32, default='')
    date_created = m.DateTimeField(auto_now_add=True)
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

    class Admin:
        list_display = ['user', 'is_private', 'url',
            'default_to_private_entry']
        list_filter = ['is_private', 'default_to_private_entry']
        ordering = ['user']
        

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

    