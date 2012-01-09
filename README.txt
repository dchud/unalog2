This is unalog2.  It's a from-scratch rewrite of the original unalog social
bookmarking application.  It was written by Dan Chudnov (dchud at umich edu)
who also wrote the original application starting in 2003.

unalog2 is a Python app that uses Django, PostgreSQL, and Solr.  

unalog2 is licensed under an MIT-style license; see LICENSE.txt.


REQUIREMENTS
------------

These are the versions of major dependencies used for development and
deployment at unalog.com.

Python 2.6+
Django 1.3+
PostgreSQL 8.4+
Java 6
Solr 1.3


INSTALLATION/DEPLOYMENT
-----------------------

This is designed to work well under common low-to-middle level VPS
or dedicated hosting.  I run it with apache2 and mod_wsgi on Ubuntu
10.04 LTS.

Install ubuntu packages (and dependencies as needed) for:

    python2.6 python2.6-dev 
    # python-virtualenv (optional, but useful)
    # python-setuptools (optional, use if you don't want a virtualenv)
    postgresql-8.4 postgresql-client-8.4 postgresql-server-dev-8.4
    openjdk-6-jdk 
    solr-tomcat
    libapache2-mod-wsgi 

Set the default encoding of your python installation to 'utf8'.  I don't
know the 100% "right" way to do this these days, but in my ubuntu/osx
python 2.6 setups, I end up putting something like this:

    import sys
    sys.setdefaultencoding('utf8')

...into /usr/lib/python2.6/sitecustomize.py at the bottom.  You'll know
it's right when you can do this and get 'utf8':

    $ python
    Python 2.6.5 (r265:79063, Apr 16 2010, 13:09:56) 
    [GCC 4.4.3] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import sys
    >>> sys.getdefaultencoding()
    'utf8'

Install non-.deb python dependencies using pip.  (NOTE: you might prefer
to do this inside a virtualenv; if not, use easy_install or pip.)

    $ pip install -r requirements.txt

This should install the following:

    django
    feedparser
    psycopg2
    simplejson
    solrpy 

Set up solr config.  Note that tomcat is probably running on port 8080;
check in /etc/tomcat6/server.xml.  Presuming it is running on port 8080,
solr is probably at localhost:8080/solr.  Because solr's http interface
is how you add, query, and delete data from solr, this should not be
visible outside of localhost.

Move the original /etc/solr/conf/schema.xml aside and copy
$UNALOG/base/schema.xml to /etc/solr/conf/schema.xml.  The default solr
schema is used when solr is first started up with tomcat.  Because unalog
has a different schema, we need to stop solr, remove the tiny index solr
created at startup with the old schema, and restart tomcat.  Solr will
then restart and create a new index based on our schema.

    % sudo /etc/init.d/tomcat6 stop
    % sudo rmdir /var/lib/solr/data/index
    % sudo /etc/init.d/tomcat6 start

Set up postgresql config.  Username below just a sample, pick your own.

    Create a user:
    % sudo su postgres
    % createuser --createdb --pwprompt unalog2user05  # pick your own
        (set the pass. remember it. :)
    % exit

    As yourself/sudoing:
    - adjust /etc/postgresql/8.4/main/pg_hba.conf appropriately
    - restart postgres if needed (sudo /etc/init.d/postgresql-8.4 restart).

    % createdb -U unalog2user05 unalog2db05  # pick your own name
    
Set up unalog config.  Examine settings.py for the defaults.  The last thing
this file does is look for a "local_settings.py" file.  This is where you'll 
put your own local settings.

Create a file called "local_settings.py" in the same directory as settings.py.
In that file, set at least the following:

    Set the following at least:
    - ADMINS
    - DATABASES
    - REALM # should be unique to your site/instance
    - SECRET_KEY
    - SOLR_URL # e.g. 'http://localhost:8080/solr', depending on tomcat conf
    - TEMPLATE_DIRS
    - UNALOG_URL # e.g. 'http://localhost:8000', leaving off trailing slash

    Prep the db schema:
    % python manage.py syncdb
        (this should create a lot of tables. create a superuser.)

    Run the app just to see if it works:
    % python manage.py runserver
        (visit http://localhost:8000/ or wherever the dev server starts)

    You should be able to see unalog up and running.

Finally, to quickly test the whole system:

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

For apache2+mod_wsgi deployments:

    Add the content of $UNALOG2/base/apache.conf to an appropriate
    /etc/apache2/sites-available.  Be sure to set the root path in 
 	all the obvious places.  Be sure this config will align with what
 	you set UNALOG_URL to in unalog2's settings.py.

	Set the local path to the parent of the unalog2 dir inside of 
	$UNALOG2/base/apache.wsgi.
	
	Restart apache2 and visit your site.
	
