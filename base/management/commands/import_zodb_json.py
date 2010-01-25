#!/usr/bin/env python

import optparse
from optparse import OptionParser
import os
import os.path
import traceback

import iso8601
import simplejson as json

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db import connection

from solr import SolrConnection
from solr.core import UTC, utc_from_string

from unalog2.base import models as m
from unalog2.settings import SOLR_URL



def add_user (old={}):
    user = User.objects.create_user(username=old['id'],
        email=old.get('email', ''),
        password=old['new_password'])
    user.password = old['new_password']
    user.is_superuser = bool(old.get('is_admin', False)) or False
    user.is_staff = bool(old.get('is_admin', False)) or False
    user.is_active = bool(old.get('is_active', False)) or False
    old_name = old.get('name', '') or ''
    if old_name:
        # Note: name lengths limited to 30 chars by django auth_user defaults,
        # hence the [:30]s
        if ' ' in old_name:
            name_tokens = old_name.split(' ')
            user.first_name = name_tokens[0][:30]
            if len(name_tokens) >= 2:
                user.last_name = name_tokens[1]
            else:
                user.last_name = ' '.join(name_tokens[1:])[:30]
        else:
            user.first_name = old_name[:30]

    try:
        profile = user.get_profile()
    except:
        # Stringy
        profile = m.UserProfile(user=user)
        for att in ['url',  'token', 'tz']:
            setattr(profile, att, old.get(att, '') or '')
        # Booleanish
        for att in ['is_private', 'default_to_private_entry']:
            setattr(profile, att, bool(old.get(att, False)) or False)
    user.save()
    profile.save()
    return user


def add_group (old={}):
    new_group, created = Group.objects.get_or_create(name=old['id'])
    if not created:
        print 'WARNING, DUPLICATE GROUP:', new_group.name
        return new_group
    print 'Adding group %s' % new_group.name
    new_group.save()
    profile = m.GroupProfile(group=new_group,
        desc=old['desc'],
        is_private=bool(old['is_private']),
        stoken=old.get('stoken', '') or '')
    profile.save()
    return new_group


def get_iso_date (d):
    date = iso8601.parse_date(d)
    return date.astimezone(UTC())
    
def solr_date_string (d):
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')

def date_string (d):
    return d.strftime('%Y-%m-%d %H:%M:%S')

def fix_group_dates (group):
    try:
        first_e = group.entries.order_by('date_created')[:1][0]
        profile = group.get_profile()
        profile.date_created = first_e.date_created
        profile.save()
        print 'Updated group "%s".date_created:' % group, group.get_profile().date_created
    except:
        #print traceback.print_exc()
        print 'No entries found for group:', group

 
def add_entry (old={}):
    pass


def main (options):
    cursor = connection.cursor()
    datadump_dir = options['directory']
    print 'Loading data from %s' % datadump_dir
    print 'Loading groups'
    old_groups = json.load(open('%s/group.json' % datadump_dir))
    print 'Found %s groups' % len(old_groups)
    for old_group_name, old_group in old_groups.items():
        new_group = add_group(old_group)
        print 'Saved new group %s from old group %s' % (new_group.id, new_group.name)
    
    for user_json in os.listdir('%s/users' % datadump_dir):
        if not user_json.endswith('.json'):
            continue
        print 'Loading %s' % user_json[:-5]
        old_user = json.load(open('%s/users/%s' % (datadump_dir, user_json)))
        new_user = add_user(old_user)
        print 'Saved new user %s from old user %s' % \
            (new_user.id, new_user.username)
        for group in old_user['groups']:
            print 'Adding to group %s' % group
            new_user.groups.add(m.Group.objects.get(name=group))
            new_user.save()
        for invite in old_user['group_invites']:
            print 'Copying invite to group %s' % invite
            new_user.group_invites.add(m.Group.objects.get(name=invite))
            new_user.save()
        for f in old_user['filters']:
            print 'Adding filter on "%s" (%s)' % (f['value'], f['attr'])
            new_filter = m.Filter(user=new_user,
                attr_name=f['attr'], 
                is_active=f['is_active'],
                is_exact=f['is_exact'], 
                value=f['value'])
            new_filter.save()
        for e_dict in old_user['entries']:
            e = m.Entry(user=new_user)
            for attr in ['title', 'comment', 'content']:
                setattr(e, attr, e_dict.get(attr, '') or '')
            url_value = e_dict.get('url', '')[:500]
            try:
                url_value_encoded = unicode(url_value).encode('utf8')
                url, created = m.Url.objects.get_or_create(value=url_value_encoded)
                e.url = url
            except UnicodeEncodeError:
                print 'Unable to copy over url:', url
                print traceback.print_exc()
            e.is_private = bool(e_dict.get('is_private', False)) or False

            date = get_iso_date(e_dict['date'])
            date_str = date_string(date)
            e.date_created = date_str
            e.save(solr_index=False)

            # groups
            for g in e_dict.get('groups', []):
                e.groups.add(m.Group.objects.get(name=g))

            # tags
            tags = e_dict.get('tags', [])
            e.add_tags(tags)
            
            # Note: date_modified will always self-update after API updates
            # so drop down to db
            #clean_date_str = e.date_created.isoformat().replace('T', ' ')
            cursor.execute("""
                UPDATE base_entry 
                SET date_created='%s', date_modified='%s' 
                WHERE id=%s
                """ % (date_str, date_str, e.id))

            if options['index']:
                e.solr_index()
            
        # A lovely little cheat
        new_user.date_joined = new_user.entries.iterator().next().date_created
        new_user.save()
        new_user_profile = new_user.get_profile()
        new_user_profile.save()
        
    for group in m.Group.objects.all():
        fix_group_dates(group)



class Command(BaseCommand):
    directory_option = optparse.make_option('--dir',
        action='store', dest='directory', default='datadump',
        help='json datadump directory')
    reset_option = optparse.make_option('--reset', 
        action='store_true', dest='reset', default=False,
        help='Reset (empty) data in tables before starting')
    index_option = optparse.make_option('--index',
        action='store_true', dest='index', default=False,
        help='Index imported entries in Solr')
    option_list = BaseCommand.option_list + (directory_option, reset_option,
        index_option)
    help = 'import a directory of json data from a zodb dump'

    def handle(self, **options):
        cursor = connection.cursor()
        if options['reset']:
            print 'Resetting tables'
            print 'Deleting all Tags'
            cursor.execute("DELETE FROM base_entrytag")
            print 'Deleting all Users'
            for u in User.objects.exclude(id=1):
                u.delete()
            cursor.execute("DELETE FROM auth_user")
            cursor.execute("DELETE FROM auth_user")
            print 'Deleting all Groups'
            for g in Group.objects.all():
                g.delete()
            
    
        main(options)
