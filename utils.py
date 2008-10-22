import logging
from datetime import timedelta, tzinfo, datetime, time
from google.appengine.api import urlfetch

SBS_SITE = 'http://www.sbstransit.com.sg/mobileiris'

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
