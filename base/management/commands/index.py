import optparse
import os.path

from solr import SolrConnection

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, reset_queries

from base import models as m
from settings import SOLR_URL

MAX_DOCS_PER_ADD = 5
COMMIT_FREQUENCY = 50

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
        SLICE_SIZE = MAX_DOCS_PER_ADD * COMMIT_FREQUENCY 
        slices = [x for x in range(entries.count()) \
            if x % SLICE_SIZE == 0]
        for s in slices:
            print 'indexing %s to %s...' % (s, s+SLICE_SIZE)
            entry_slice = entries[s:s+SLICE_SIZE]
            for entry in entry_slice:
                counter += 1
                docs.append(entry.solr_doc)
                if len(docs) == MAX_DOCS_PER_ADD:
                    try:
                        self.solr.add_many(docs)
                    except:
                        print 'BAD RECORD:', [d['id'] for d in docs]
                    del(docs)
                    docs = []
                    reset_queries()
                    if counter % (COMMIT_FREQUENCY * MAX_DOCS_PER_ADD) == 0:
                        print 'committing at count:', counter
                        self.solr.commit()
        # Don't miss the leftovers
        self.solr.add_many(docs)
                
            
