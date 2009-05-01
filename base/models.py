from cStringIO import StringIO
from datetime import datetime
import hashlib
import re

import iso8601 

from solr import SolrConnection, UTC, utc_from_string

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import connection, models as m



class GroupProfile (m.Model):
    group = m.OneToOneField(Group, related_name='profile')
    desc = m.TextField(blank=True)
    is_private = m.BooleanField(default=False, db_index=True)
    stoken = m.CharField(blank=True, max_length=32, default='')
    date_created = m.DateTimeField(auto_now_add=True)
    date_modified = m.DateTimeField(auto_now=True)
    # NOTE: Am removing the notion of a group admin by choice
        
    class Meta:
        ordering = ['group']

# Duckpunch Group to offer up profile like User's get_profile just
# because it looks weird to use User.get_profile and Group.profile
def get_profile(group):
    return group.profile
    
Group.get_profile = get_profile


class UserProfile (m.Model):
    user = m.ForeignKey(User, unique=True)
    is_private = m.BooleanField(default=False, db_index=True)
    default_to_private_entry = m.BooleanField(default=False)
    url = m.URLField(blank=True, verify_exists=True)
    token = m.CharField(blank=True, max_length=32)
    tz = m.CharField(blank=True, max_length=6)
    group_invites = m.ManyToManyField(Group, related_name='invitees')
    date_modified = m.DateTimeField(auto_now=True)


class Filter (m.Model):
    user = m.ForeignKey(User, related_name='filters')
    attr_name = m.CharField(max_length=20)
    value = m.CharField(max_length=50)
    is_exact = m.BooleanField(default=False)
    is_active = m.BooleanField(default=True)
    date_created = m.DateTimeField(auto_now_add=True, db_index=True)
    date_modified = m.DateTimeField(auto_now=True)
    

# Bad chars for tags
BAD_CHARS = """ ~`@#$%^&*()?\/,<>;\"'"""
RE_BAD_CHARS = re.compile(r'[%s]' % BAD_CHARS)

class Tag (m.Model):
    name = m.CharField(max_length=50, unique=True)
    
    def __unicode__ (self):
        return self.name


class EntryTag (m.Model):
    entry = m.ForeignKey('Entry', related_name='tag_set', db_index=True)
    tag = m.ForeignKey(Tag, related_name='entry_set', db_index=True)
    sequence_num = m.SmallIntegerField(default=0)
    
    class Meta:
        unique_together = ['entry', 'tag', 'sequence_num']
        ordering = ['sequence_num']

    @classmethod
    def count(self, user=None, request_user=None, order='freq'):
        """
        Get a list of most frequently used tags (and counts), either for the
        whole site, or for a particular user.  Filter out tags used with private
        entries.
        """
        if user == request_user:
            private_clause = ''
        else:
            # NOTE: postgresql-specific value
            private_clause = 'AND base_entry.is_private is false'

        if user:
            user_clause = 'AND base_entry.user_id=%s' % user.id
        else: 
            user_clause = ''
        order_clause = 'ORDER BY COUNT(tag_id) DESC, name'

        if order == 'alpha':
            order_clause = 'ORDER BY name, COUNT(tag_id)'
        elif order == 'recent':
            order_clause = 'ORDER BY tag_id DESC, name'

        sql = """
            SELECT COUNT(tag_id), name, tag_id
            FROM base_entrytag, base_entry, base_tag, auth_user
            WHERE base_entry.id=base_entrytag.entry_id 
            AND base_tag.id=base_entrytag.tag_id 
            AND auth_user.id=base_entry.user_id
            AND auth_user.is_active is true
            %s
            %s
            GROUP BY tag_id, name 
            %s
            """ % (private_clause, user_clause, order_clause)
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows        


class Url (m.Model):
    value = m.CharField(max_length=500)
    md5sum = m.CharField(max_length=32, db_index=True)

    def __unicode__(self):
        return '<Url %s: %s>' % (self.id, self.value)
         
    @property
    def md5(self):
        """
        Provide a simple md5 value for lookups/comparisons.
        """
        return hashlib.md5(self.value).hexdigest()

    def save(self, force_insert=False, force_update=False):
        """
        Set the md5sum automatically.
        """
        self.md5sum = self.md5
        super(Url, self).save(force_insert, force_update)
        
        
        
class Entry (m.Model):
    ENTRY_TYPE_CHOICES = [
        ('l', 'Web link'),
        ]
        
    # Default to 'web link' just to save a step
    etype = m.CharField(max_length=1, choices=ENTRY_TYPE_CHOICES,
        default=ENTRY_TYPE_CHOICES[0][0], db_index=True)
    user = m.ForeignKey(User, related_name='entries')
    title = m.TextField()
    url = m.ForeignKey(Url, related_name='entries')
    comment = m.TextField(blank=True)
    is_private = m.BooleanField(default=False, db_index=True)
    content = m.TextField(blank=True)
    groups = m.ManyToManyField(Group, related_name='entries')
    date_created = m.DateTimeField(auto_now_add=True, db_index=True)
    date_modified = m.DateTimeField(auto_now=True)
    
    def __unicode__ (self):
        return '<Entry: %s (%s)>' % (self.id, self.user.username)
        
    class Meta:
        verbose_name_plural = 'entries'
        
    def add_tags(self, tag_list=[]):
        """
        Add one or more tags, in order.  Does nothing if there are none.
        """
        # Remove empty tags like ''
        tag_list = [tag_str for tag_str in tag_list if not tag_str == '']

        # Remove bad tags, for bad chars or too lengthy
        for tag_str in tag_list:
            # Keep 'em cleanish
            if RE_BAD_CHARS.search(tag_str):
                tag_list.remove(tag_str)

            # Keep 'em shortish
            if len(tag_str) > 30:
                tag_list.remove(tag_str)

            # Remove repeats
            while tag_list.count(tag_str) > 1:
                tag_list.remove(tag_str)
        
        for i in range(len(tag_list)):
            tag, created = Tag.objects.get_or_create(name=tag_list[i])
            et = EntryTag(entry=self, tag=tag, sequence_num=i)
            et.save()
        
    @property
    def other_count(self, public_only=True):
        """
        Return the number of other entries that use the same URL.  Available
        as a property to count public_only entries for easy use in templates.
        """
        qs = self.__class__.objects.filter(url=self.url)
        qs = qs.exclude(id=self.id)
        if public_only:
            qs.filter(is_private=False)
        return qs.count()

    @property
    def solr_doc(self):
        """
        Returns a dict representation suitable for solr indexing.
        """
        # Weird date machinations are for varying index-time date value states
        date_created = self.date_created
        if type(date_created) == type(''):
            date_created = date_created.replace(' ', 'T')
            date_created = date_created + 'Z'
        else:
            date_created = date_created.strftime('%Y-%m-%dT%H:%M:%SZ')

        d = {'id': self.id,
            'user': self.user.username, 
            'user_id': self.user.id,
            'is_private_entry': self.is_private,
            'is_private_user': self.user.get_profile().is_private,
            'is_active_user': self.user.is_active,
            'title': self.title,
            'url': self.url.value,
            'comment': self.comment,
            'content': self.content,
            'date_created': date_created,
            #'date_modified': self.date_modified,
            'tag': [entry_tag.tag.name for entry_tag in self.tag_set.all()],
            'group': [g.name for g in self.groups.all()],
            }
        return d

    def solr_index(self):
        """
        Write out to solr
        """
        solr_conn = SolrConnection(settings.SOLR_URL)
        solr_conn.add(**self.solr_doc)
        solr_conn.commit()

    def save(self, force_insert=False, force_update=False, solr_index=True):
        """
        Override the built-in save() to write out to solr.
        """
        # Write out the to db
        super(Entry, self).save(force_insert, force_update)
        if solr_index:
            self.solr_index

    def solr_delete(self):
        """
        Remove from solr index
        """
        solr_conn = SolrConnection(settings.SOLR_URL)
        solr_conn.delete_query('id:%s' % self.id)
        solr_conn.commit()
        
    def delete(self, solr_delete=True):
        """
        Override the built-in delete() to delete from solr.
        """
        
        # Delete from solr first, or lose your self 
        if solr_delete:
            self.solr_delete()
        super(Entry, self).delete()
        