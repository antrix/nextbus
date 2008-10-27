import logging
from datetime import timedelta, tzinfo, datetime, time
from google.appengine.api import urlfetch

SBS_SITE = 'http://www.sbstransit.com.sg/mobileiris'
LTA_SITE = 'http://www.publictransport.sg/public/ptp/en/Getting-Around/' \
            'ArrivaltimeResults.html?hidServiceNoValue='

PAGE_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>%(title)s</title>
        <meta name="viewport" 
            content="width=320; initial-scale=1; maximum-scale=1; user-scalable=1;"/>
        <style type="text/css">
            body, td, th {font-size: smaller;}
        </style>
    </head>
<body>
%(body)s
</body>
</html>"""

AJAX_PAGE_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>%(stop)s | nextbus</title>
        <meta name="viewport" 
            content="width=320; initial-scale=1; maximum-scale=1; user-scalable=1;"/>
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
        [<a id="refresh-link" href="/stop/?number=%(stop)s">Refresh</a>] [<a href="/">Home</a>]
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

def get_url(url):
    try:
        result = urlfetch.fetch(url)
        if result.status_code != 200:
            logging.warn('Error code %s while fetching url: %s' % (result.status_code, url))
            if result.status_code != 404:
                logging.debug('Details for url fetch error: %s' % result.content)
            raise HTTPError(url, result.status_code, result.content)
        else:
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

