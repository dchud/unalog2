#!/usr/bin/env python

from optparse import OptionParser
import os

import simplejson as json

from unalog2.base import models as m



def add_user (old={}):
	new_user = m.UnaUser()
	new_user.unaid = old['id']
	print 'Adding user %s' % new_user.unaid
	# Stringy
	for att in ['name', 'url', 'email', 'old_password', 'new_password',
		'token', 'tz']:
		setattr(new_user, att, old.get(att, '') or '')
	# Booleanish
	for att in ['is_active', 'is_admin', 'is_private', 'default_to_private_entry']:
		setattr(new_user, att, old.get(att, False) or False)
	new_user.save()
	return new_user
	

def add_group (old={}):
	new_group = m.UnaGroup()
	new_group.unaid = old['id']
	print 'Adding group %s' % new_group.unaid
	new_group.name = old['name']
	new_group.desc = old['desc']
	new_group.is_private = old['is_private']
	new_group.stoken = old.get('stoken', '') or ''
	new_group.save()
	return new_group

def add_entry (old={}):
	pass
	

def main (options, args):
	print 'Loading data from %s' % options.directory
	print 'Loading groups'
	old_groups = json.load(open('%s/group.json' % options.directory))
	new_groups = {}
	print 'Found %s groups' % len(old_groups)
	for old_group_name, old_group in old_groups.items():
		new_group = add_group(old_group)
		print 'Saved new group %s from old group %s' % (new_group.id, new_group.unaid)
		new_groups[new_group.unaid] = new_group
		
	old_users = []
	new_users = {}
	for user_json in os.listdir('%s/users' % options.directory):
		if not user_json.endswith('.json'):
			continue
		print 'Loading %s' % user_json[:-5]
		old_users.append(json.load(open('%s/users/%s' % (options.directory, user_json))))
		
	for old_user in old_users:
		new_user = add_user(old_user)
		print 'Saved new user %s from old user %s' % (new_user.id, new_user.unaid)
		for group in old_user['groups']:
			print 'Adding to group %s' % group
			new_user.groups.add(new_groups[group])
		for invite in old_user['group_invites']:
			print 'Copying invite to group %s' % invite
			new_user.group_invites.add(new_groups[invite])
		for f in old_user['filters']:
			print 'Adding filter on "%s" (%s)' % (f['value'], f['attr'])
			new_user.filters.add(m.Filter(attr_name=f['attr'], is_active=f['is_active'],
				is_exact=f['is_exact'], value=f['value']))
		new_users[new_user.unaid] = new_user



if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-d', '--directory', dest='directory',
		help='Directory containing zodb json dump', default='datadump')
	parser.add_option('-r', '--reset', dest='reset',
		action='store_true', default=False,
		help='Reset (empty) data in tables before starting')
	options, args = parser.parse_args()
	
	if options.reset:
		print 'Resetting tables'
		print 'Deleting all UnaUsers'
		for u in m.UnaUser.objects.all():
			u.delete()
		print 'Deleting all UnaGroups'
		for g in m.UnaGroup.objects.all():
			g.delete()
			
	
	main(options, args)