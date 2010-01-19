This is unalog2.  It's a total rewrite of the original unalog social
bookmarking application.  It was written by Dan Chudnov (dchud at umich edu)
who also wrote the original application in 2003.

The original application was a Python app that used Quixote1, ZODB, and
PyLucene.  This is a Python app that uses Django, PostgreSQL, and Solr.  This
app can be fed by a JSON export from the original application; that's how the
main site at unalog.com was refed when the site was restarted in early 2010.

The site broke in late 2008 due to some negligence and general performance
problems.  It had been "out there" on the net for five years without a lot of
upkeep, which isn't so bad, I suppose.  The site was down for all of 2009
because the rewrite got stalled.  Stuff happens.



REQUIREMENTS
------------

These are the versions of dependencies used for development and deployment at
unalog.com.

Python 2.6.4
Django 1.1.1
PostgreSQL 8.4
psycopg2 2.0.13
Solr 1.3
solrpy 0.9
simplejson 2.0.9



DEPLOYMENT
----------

This is designed to work well under common low-to-middle level VPS or
dedicated hosting.  I run it with apache2 and mod_wsgi.