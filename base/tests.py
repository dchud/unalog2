"""
IMPORTANT!

For these tests to run you'll need to run a test solr instance on a port 9999 
so that you don't stomp on your real production solr.
    
    java -Djetty.port=9999 -DSTOP.PORT=9998 -jar start.jar

"""

from django.conf import settings
from django.test import TestCase, Client

from unalog2.base import models as m

class UnalogTests(TestCase):
    fixtures = ['test_account.json']
    settings.SOLR_URL = "http://localhost:9999/solr"

    def test_add_entry(self):
        client = Client()
        self.assertTrue(client.login(username='unalog', password='unalog'))
        entry = {
                    'url':          'http://example.com/',
                    'title':        'hey example.com!',
                    'is_private':   False,
                    'tags':         'unalog yeah',
                    'comment':      'this is just an example see?',
                    'content':      'example yeah! example yeah!',
                    'submit':       None

                }

        response = client.post('/entry/new', entry)
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

