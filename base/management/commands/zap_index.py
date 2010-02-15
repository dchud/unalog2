import optparse
import os.path
import sys

from django.core.management.base import BaseCommand, CommandError

from solr import SolrConnection

from settings import SOLR_URL

class Command(BaseCommand):
    user_option = optparse.make_option('--user',
        action='store', dest='user',
        help='name of user whose entries to purge')
    option_list = BaseCommand.option_list + (user_option,)
    help = "remove all or user-specific entries from solr"
    args = 'an optional username'

    def handle(self, **options):
        solr = SolrConnection(SOLR_URL)
        if options['user']:
            solr.delete_query('user:%s' % options['user'])
        else:
            solr.delete_query('id:[* TO *]')
        solr.commit()
