import hashlib

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
    

class Tag (m.Model):
    name = m.CharField(max_length=50, unique=True)
    
    def __unicode__ (self):
        return self.name
        
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
        user_clause = 'AND base_entry.user_id=%s' % user.id
        order_clause = 'ORDER BY COUNT(tag_id) DESC, name'

        if order == 'alpha':
            order_clause = 'ORDER BY name, COUNT(tag_id)'
        sql = """
            SELECT COUNT(tag_id), name 
            FROM base_entry_tags, base_entry, base_tag 
            WHERE base_entry.id=base_entry_tags.entry_id 
            %s
            AND base_tag.id=base_entry_tags.tag_id 
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

    @property
    def md5(self):
        return hashlib.md5(self.value).hexdigest()

    def save(self, force_insert=False, force_update=False):
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
    tags = m.ManyToManyField(Tag, related_name='entries')
    groups = m.ManyToManyField(Group, related_name='entries')
    date_created = m.DateTimeField(auto_now_add=True, db_index=True)
    date_modified = m.DateTimeField(auto_now=True)
    
    def __unicode__ (self):
        return '<Entry: %s (%s)>' % (self.id, self.user.username)
        
    class Meta:
        verbose_name_plural = 'entries'
        
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

