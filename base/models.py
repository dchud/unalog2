from django.db import models as m


class UnaGroup (m.Model):
	unaid = m.CharField(max_length=100, unique=True)
	name = m.CharField(max_length=100)
	desc = m.TextField(blank=True)
	is_private = m.BooleanField(default=False, db_index=True)
	stoken = m.CharField(max_length=32)


class UnaUser (m.Model):
	unaid = m.CharField(max_length=100, unique=True)
	name = m.CharField(max_length=100, unique=True)
	email = m.EmailField()
	old_password = m.CharField(max_length=100)
	new_password = m.CharField(max_length=100)
	is_active = m.BooleanField(default=True)
	is_admin = m.BooleanField(default=False)
	is_private = m.BooleanField(default=False, db_index=True)
	default_to_private_entry = m.BooleanField(default=False)
	url = m.URLField(blank=True, verify_exists=True)
	token = m.CharField(max_length=32)
	tz = m.CharField(max_length=6)
	groups = m.ManyToManyField(UnaGroup, related_name='users')
	group_invites = m.ManyToManyField(UnaGroup, related_name='invitees')
	

class Filter (m.Model):
	user = m.ForeignKey(UnaUser, related_name='filters')
	attr_name = m.CharField(max_length=20)
	value = m.CharField(max_length=50)
	is_exact = m.BooleanField(default=False)
	is_active = m.BooleanField(default=True)