#!/usr/bin/env python

"""
This is a delicious to unalog import tool. You'll need to export your
delicious links and save them as a file ... it should be html. Then
you run this script with your unalog username and password with the 
delicious export file:

  ./d2u.py --username me --password secret delicious-20101216.htm

Use --unalog if you want to target another unalog instance.

You will need lxml, html5lib and httplib2 installed:

    easy_install lxml
    easy_install html5lib
    easy_install httplib2

"""

import httplib2
import json
import optparse
import os
import socket
import sys
import time
import urllib2

from html5lib import HTMLParser, treebuilders
from lxml import etree

socket.setdefaulttimeout(10)

opt_parser = optparse.OptionParser()
opt_parser.add_option('-u', '--username', dest='username')
opt_parser.add_option('-p', '--password', dest='password')
opt_parser.add_option('-n', '--unalog', dest='unalog', 
                      default="http://unalog.com")
opt_parser.add_option('-s', '--skip', type=int, dest='skip', default=0)
opt_parser.add_option('-c', '--check', action='store_true', dest='check')

opts, args = opt_parser.parse_args()

if len(args) != 1:
    opt_parser.error("must supply delicious bookmarks html file")
elif not os.path.isfile(args[0]):
    opt_parser.error("no such file: %s" % args[0])
else:
    delicious = args[0]

if not opts.username or not opts.password:
    opt_parser.error("must supply --username or --password")

# parse the delicious html bookmarks export 
xhtml = "http://www.w3.org/1999/xhtml"
parser = HTMLParser(tree=treebuilders.getTreeBuilder("lxml"))
doc = parser.parse(open(delicious))

# create http client
h = httplib2.Http()
h.add_credentials(opts.username, opts.password)
unalog = opts.unalog.rstrip("/") + "/entry/new"

summary = {}
count = 0

for dt in doc.findall(".//{%s}dt" % xhtml):
    count += 1
    if opts.skip > 1 and count < opts.skip:
        continue

    # get the bookmark from the dt
    a = dt.find('{%s}a' % xhtml)
    b  = a.attrib

    # see if there's a comment in the next element
    e = dt.getnext()
    if e is not None and e.tag == "{%s}dd" % xhtml:
        comment = e.text
    else:
        comment = None

    # convert the epoch time into rfc 3339 time
    t = time.localtime(int(b["add_date"]))
    t = time.strftime('%Y-%m-%dT%H:%M:%S%z', t)

    # get the content at the url only if it looks like html or text
    url = b["href"]
    try:
        resp = urllib2.urlopen(url)
        content = resp.read()
        status = resp.code 
        summary[status] = summary.get(status, 0) + 1
        content_type = resp.headers['content-type']
        if 'html' in content_type or 'text' in content_type:
            content = content.decode('utf-8', 'replace')
        else:
            content = None
    except urllib2.HTTPError, e:
        content = None
        status = e.code
    except urllib2.URLError, e:
        content = None
        status = e.reason
    except Exception, e:
        content = None
        status = str(type(e))

    summary[status] = summary.get(status, 0) + 1
    print "\t".join([url, str(status)])

    # don't bother posting to unalog if we're just checking
    if opts.check:
        continue

    # build the bookmark entry
    entry = {
        "url": b["href"],
        "title": a.text,
        "tags": b["tags"].replace(',', ' '),
        "private": b["private"] == 1,
        "date_created": t,
        "comment": comment,
        "content": content
    }

    # send the bookmark to unalog as json
    resp, content = h.request(unalog, "POST", body=json.dumps(entry),
            headers={"content-type": "application/json"})

    if resp.status not in [200, 201, 302]:
        print "post to unalog failed! %s" % url



print "imported %s bookmarks" % count
print "response summary: %s" % summary
