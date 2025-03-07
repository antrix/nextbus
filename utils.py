import logging
import random
from datetime import timedelta, tzinfo, datetime, time

from google.appengine.api import urlfetch

SBS_SITE = 'http://www.sbstransit.com.sg/iris_map'
LTA_SITE = 'http://www.publictransport.sg/publish/mobile/en/busarrivaltime.jsp'

PAGE_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>%(title)s</title>
        <meta name="viewport" 
            content="width=device-width, maximum-scale=1.0"/>
        <style type="text/css">
            body, td, th {font-size: smaller;}
        </style>
    </head>
<body>
%(body)s
    <p style="font-size: smaller; color: #8B7D6B;">
        <strong>NOTE:</strong>: I'll be shutting down this site for good on <strong>1<sup>st</sup> November</strong>. So long, and thanks for all the fish!
    </p>
</body>
</html>"""

AJAX_PAGE_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>%(stop)s | NextBus</title>
        <meta name="viewport" 
            content="width=device-width, maximum-scale=1.0"/>
        <style type="text/css">
            body, td, th {font-size: smaller;}
            table {display: none;}
            #error {font-size: smaller; color: red; margin: 1em;}
        </style>
        <script type="text/javascript" 
            src="http://ajax.googleapis.com/ajax/libs/jquery/1.2/jquery.min.js"></script>
        <script type="text/javascript" src="/static/nextbus.js"></script>
    </head>
<body>
<div>Services at stop <span id="stop-number">%(stop)s</span>.</div>
<div id="stop-description"></div>
<div id="error"></div>
<font>
    <table id="grid" border="0" cellpadding="2">
        <thead><tr align="left"><th></th><th>Next</th>
        <th>Subsequent</th></tr></thead>
        <tbody></tbody>
        </table><br/>
</font>
    <p style="font-size: smaller;">
        [<a id="refresh-link" href="/stop/?xhr=1&number=%(stop)s">Refresh</a>] [<a href="/">Home</a>]
    </p>
    <p style="font-size: smaller; color: #8B7D6B;">
        <strong>NOTE:</strong>: I'll be shutting down this site for good on <strong>1<sup>st</sup> November</strong>. So long, and thanks for all the fish!
    </p>
</body>
</html>"""

class HTTPError(Exception):
    def __init__(self, url, code, content=""):
        self.url = url
        self.code = code
        self.content = content

    def __str__(self):
        return "HTTPError %s on url %s" % (self.url, self.code)

def _urlfetch2(url):
    maximum = 3
    for count in range(maximum):
        try:
            return urlfetch.fetch(url, headers={'User-Agent': 'NextBus'})
        except urlfetch.DownloadError:
            if count == (maximum-1):
                raise

def get_url(url, payload=None, method=urlfetch.GET, deadline=None):
    try:
        logging.debug("Fetching URL: %s", url)

        headers = {'User-Agent': 'Dalvik/1.2.0 (Linux; U; Android 2.2; Nexus One Build/FRF91)'}
        if payload:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            result = urlfetch.fetch(url=url, payload=payload, method=urlfetch.POST,
                                    headers=headers, deadline=deadline)
        else:
            result = urlfetch.fetch(url=url, method=method, headers=headers, deadline=deadline)
        
        logging.debug("Fetched URL: %s", url)

        if result.status_code != 200:
            logging.warn('Error code %s while fetching url: %s' % (result.status_code, url))
            if result.status_code != 404:
                logging.debug('Details for url fetch error: %s' % result.content)
            #logging.debug("URL contents: %s", result.content)
            raise HTTPError(url, result.status_code, result.content)
        else:
            #logging.debug("URL contents: %s", result.content)
            return result.content
    except urlfetch.Error, e:
        logging.warn("Error fetching url %s" % url, exc_info=True)
        raise e

class SG_tzinfo(tzinfo):
    """Implements Singapore timezone"""

    def __repr__(self):
        return "Asia/Singapore"
    
    def utcoffset(self, dt):
        return timedelta(hours=8)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.__repr__()

def is_day_time():
    sg_tz = SG_tzinfo()
    min = time(23, 45, 0, 0, sg_tz)
    max = time(6, 0, 0, 0, sg_tz)
    now = datetime.now(sg_tz).timetz()

    if (min < now) or (now < max):
        return False
    else:
        return True

