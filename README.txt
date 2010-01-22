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

Python 2.5.2/2.6.4
Django 1.1.1
PostgreSQL 8.4
psycopg2 2.0.13
Solr 1.3
solrpy 0.9
simplejson 2.0.9

Last I heard Django will move to Python 3 slowly so I'm going to move to
Python 3 slowly, too.  When they go, I'll go.



INSTALLATION/DEPLOYMENT
-----------------------

This is designed to work well under common low-to-middle level VPS or
dedicated hosting.  I run it with apache2 and mod_wsgi on ubuntu 8.04.

Install ubuntu packages (and dependencies) for:

    python ipython python-setuptools
    postgresql-8.3 postgresql-client-8.3 python-psycopg2
    solr-tomcat5.5
    libapache2-mod-wsgi 

Set the default encoding of your python installation to 'utf8'.  I 
don't know the 100% "right" way to do this these days, but in my
ubuntu/osx python 2.5 and 2.6 setups, I end up putting something like
this:

    import sys
    sys.setdefaultencoding('utf8')

...into /usr/lib/python2.5/sitecustomize.py at the bottom.  You'll know
it's right when you can do this and get 'utf8':

    % python
    Python 2.5.2 (r252:60911, Jan 20 2010, 21:48:48) 
    [GCC 4.2.4 (Ubuntu 4.2.4-1ubuntu3)] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import sys
    >>> sys.getdefaultencoding()
    'utf8'

Install python dependencies:

    from tarball:   Django 1.1.1
    w/easy_install: solrpy 0.9 (and iso8601, if import from zodb install)

Set up solr config.  Move the original /etc/solr/conf/schema.xml
aside and copy $UNALOG/base/schema.xml to /etc/solr/conf/schema.xml.
Note that tomcat is probably running on port 8180; check in
/etc/tomcat5.5/server.xml.  This port should *never* be visible outside
of localhost.

The default solr schema is used when solr is first started up with
tomcat.  Because unalog has a different schema, we need to stop solr,
remove the tiny index solr created at startup with the old schema, and
restart tomcat.  Solr will then restart and create a new index based on
our schema.

    % sudo /etc/init.d/tomcat5.5 stop
    % sudo rmdir /var/lib/solr/data/index
    % sudo /etc/init.d/tomcat5.5 start

Set up postgresql config.  Username below just a sample, pick your own.

    Create a user:
    % sudo su postgres
    % createuser --createdb --pwprompt unalog2user05  # pick your own
        (set the pass. remember it. :)
    % exit

    As yourself/sudoing:
    - adjust /etc/postgresql/8.3/main/pg_hba.conf appropriately
    - restart postgres if needed.

    % createdb unalog2db05  # pick your own
    
Set up unalog config.  In the directory where you unwrap unalog:

    % cp settings.py.default settings.py

    Set the following at least:
    - UNALOG_URL
    - DATABASE_NAME
    - DATABASE_USER
    - DATABASE_PASSWORD 
    - TEMPLATE_DIRS
    - SOLR_URL # e.g. 'http://localhost:8180/solr', depending on tomcat conf

    Prep the db schema:
    % python manage.py syncdb
        (this should create a lot of tables. create a superuser.)

    Run the app just to see if it works:
    % python manage.py runserver
        (visit http://localhost:8000/ or wherever the dev server starts)

    You should be able to see unalog up and running.

Finally, to test the whole system:

    - log in as the superuser you created
    - visit the /bookmarklet/ path (link is in header)
    - put a bookmarklet in your browser bookmarks bar
    - visit some random web page
    - click the 'unalog!' bookmarklet in your browser bookmarks bar
    - add some tags or a comment
    - click 'Home'. do you see your entry?
    - search for your entry (use a title word or a tag). do you
      see your entry?
    - if the answer to the last two questions was 'yes', you're up
      and running!

    
