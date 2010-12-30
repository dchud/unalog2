"""
IMPORTANT!

For these tests to run you'll need to run a test solr instance on a port 9999 
so that you don't stomp on your real production solr.
    
    java -Djetty.port=9999 -DSTOP.PORT=9998 -jar start.jar

"""

from django.conf import settings
from django.test import TestCase, Client
from django.utils import simplejson as json

from unalog2.base import models as m

class UnalogTests(TestCase):
    fixtures = ['test_account.json']
    settings.SOLR_URL = "http://localhost:9999/solr"

    test_entry = {
        'url':          'http://example.com/',
        'title':        'hey example.com!',
        'is_private':   False,
        'tags':         'unalog yeah',
        'comment':      'this is just an example see?',
        'content':      'example yeah! example yeah!',
        'submit':       None
    }

    def test_add_entry(self):
        client = Client()
        self.assertTrue(client.login(username='unalog', password='unalog'))
        response = client.post('/entry/new', self.test_entry)
        self.assertEqual(response['location'], 
                'http://testserver/entry/1/edit/')
        entry = m.Entry.objects.get(id=1)
        self.assertEqual(entry.url.value, 'http://example.com/')
        self.assertEqual(entry.title, 'hey example.com!')
        self.assertEqual(entry.is_private, False)
        self.assertEqual(entry.comment, 'this is just an example see?')
        self.assertEqual(entry.content, 'example yeah! example yeah!')
        entry_tags = entry.tags.all()
        self.assertEqual(len(entry_tags), 2)
        self.assertEqual(entry_tags[0].tag.name, 'unalog')
        self.assertEqual(entry_tags[1].tag.name, 'yeah')


    def test_add_entry_json(self):
        client = Client()
        self.assertTrue(client.login(username='unalog', password='unalog'))
        entry_json = json.dumps(self.test_entry)
        response = client.post('/entry/new', entry_json, 
                content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], 'http://testserver/entry/1/edit/')
        entry = m.Entry.objects.get(id=1)
        self.assertEqual(entry.url.value, 'http://example.com/')
        self.assertEqual(entry.title, 'hey example.com!')
        self.assertEqual(entry.is_private, False)
        self.assertEqual(entry.comment, 'this is just an example see?')
        self.assertEqual(entry.content, 'example yeah! example yeah!')
        entry_tags = entry.tags.all()
        self.assertEqual(len(entry_tags), 2)
        self.assertEqual(entry_tags[0].tag.name, 'unalog')
        self.assertEqual(entry_tags[1].tag.name, 'yeah')

    def test_add_entry_invalid_json(self):
        client = Client()
        self.assertTrue(client.login(username='unalog', password='unalog'))
        response = client.post('/entry/new', '{bad json har har;]', 
                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, 'invalid json: Expecting property name: line 1 column 1 (char 1)')

    def test_add_entry_bad_json(self):
        # remove the required url field
        bad_json = self.test_entry.copy()
        del bad_json['url']

        entry_json = json.dumps(bad_json)

        client = Client()
        self.assertTrue(client.login(username='unalog', password='unalog'))
        response = client.post('/entry/new', entry_json, 
                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, 'There was a problem with your JSON:\n\n  url: This field is required.')
