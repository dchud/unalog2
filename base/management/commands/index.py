import optparse
import os.path

from solr import SolrConnection

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, reset_queries

from unalog2.base import models as m
from unalog2.settings import SOLR_URL

MAX_DOCS_PER_ADD = 50
COMMIT_FREQUENCY = 5

class Command(BaseCommand):
    user_option = optparse.make_option('--user',
        action='store', dest='user',
        help='name of user whose entries to purge')
    option_list = BaseCommand.option_list + (user_option,)
    help = "index all or user-specific entries in solr"
    args = 'an optional username'

    def handle(self, *args, **options):
        self.solr = SolrConnection(SOLR_URL)
        self.cursor = connection.cursor()
        if options['user']:
            print "indexing user"
            self.index_entries(user=options['user'])
        else:
            print 'indexing everything'
            self.index_entries()
        print 'committing'
        self.solr.commit()
        print 'optimizing'
        self.solr.optimize()

    def index_entries(self, user=''):
        counter = 0
        entries = m.Entry.objects.all()
        if user:
            entries = entries.filter(user__username=user)
        docs = []
        print 'entry count:', entries.count()
        for entry in entries:
            counter += 1
            docs.append(entry.solr_doc)
            if len(docs) == MAX_DOCS_PER_ADD:
                try:
                    self.solr.add_many(docs)
                except:
                    print 'BAD RECORD:', [d['id'] for d in docs]
                docs = []
                reset_queries()
                if counter % (COMMIT_FREQUENCY * MAX_DOCS_PER_ADD) == 0:
                    print 'committing at count:', counter
                    self.solr.commit()
        # Don't miss the leftovers
        self.solr.add_many(docs)
                
            