import wsgiref.handlers
from datetime import timedelta, tzinfo, datetime, time
import logging
import os
import random
import re
import StringIO

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
try:
    from google.appengine.runtime import DeadlineExceededError
except:
    from google.appengine.runtime.apiproxy_errors import DeadlineExceededError

try:
    from google3.apphosting.runtime import DeadlineExceededError as DeadlineExceededError2
except:
    DeadlineExceededError2 = DeadlineExceededError

from BeautifulSoup import BeautifulSoup

SBS_SITE = 'http://www.sbstransit.com.sg/mobileiris'

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

def isvaliddomain():
    valid_list = ['sbsnextbus.appspot.com', 
             'localhost', 'localhost:9999', 'localhost:8080']
    host = os.environ['HTTP_HOST'].lower()
    for valid_host in valid_list:
        if host.endswith(valid_host):
            return True
    return False

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

class EndPoint(webapp.RequestHandler):

    def get(self):
        if not isvaliddomain():
            self.error(503)
            self.response.out.write('You are not authorized to run this' +
                    ' application on the domain %s. Please visit sbsnextbus.appspot.com directly.'
                    % os.environ['HTTP_HOST'])
            return

        if self.request.get('flushcache'):
            result = memcache.flush_all()
            response = PAGE_TEMPLATE % {
                'title': 'sbsnextbus - memcache flush', 
                'body': 'memcache flush ' + \
                            (result and 'succeeded' or 'failed')}
            self.response.out.write(response)
            return
        
        try:
            # Cast to int just to ensure we are getting a number
            stop = int(self.request.get('number'))
            stop = self.request.get('number')
        except ValueError:
            self.redirect('/?error')
            return

        # Fetch the bus services at this stop
        try:
            details = self.get_stop_details(stop)
        except (DeadlineExceededError, DeadlineExceededError2):
            redirect_url = '/stop/?number=%s&random=%s' % (stop, random.randint(1,100))
            self.redirect(redirect_url)
            logging.warn('Request preempted. Redirecting to %s' % redirect_url)
        except Exception, e:
            if isinstance(e, HTTPError) and e.code == 404:
                self.error(404)
                self.response.out.write(
                    PAGE_TEMPLATE % {
                    'title': stop + ' not found - sbsnextbus', 
                    'body': 'The requested stop ' + stop + ' could not be found.' \
                        ' Are you sure you entered the stop number correctly?' \
                        'If this problem persists, please contact' \
                        ' dsarda+nextbus@gmail.com about it.'}
                    )
            else:
                self.error(500)
                self.response.out.write(
                    PAGE_TEMPLATE % {
                    'title': 'Error - sbsnextbus', 
                    'body': 'Error processing request. Please ' \
                        '<a href="">retry</a>. If this problem persists,' \
                        ' please contact dsarda+nextbus@gmail.com about it.'}
                    )
                if not isinstance(e, HTTPError):
                    logging.error("Error getting stop details", exc_info=True)
            return

        try:
            description = details[0]
            services = details[1]
            output = StringIO.StringIO()
            output.write('<p>Services at stop %s.<br/> %s.</p>' \
                    '<font><table border="0" cellpadding="2">' \
                    '<tr align="left"><th></th><th>Next</th>' \
                    '<th>Subsequent</th></tr>' % (stop, description))
            for service in services:
                try:
                    next, subsequent = ('retry', 'retry')
                    next, subsequent = self.get_timings(stop, service)
                except (DeadlineExceededError, DeadlineExceededError2):
                    raise
                except:
                    pass

                output.write('<tr><td><a href="%s/index_mobresult.aspx?' \
                    'stop=%s&svc=%s">%s</a></td><td>%s</td><td>%s</td></tr>' \
                    % (SBS_SITE, stop, service, service, next, subsequent))

            output.write('</table><br/><a href="http://%s/stop/?number=%s">' \
                'Refresh</a></font>' % (os.environ['HTTP_HOST'].lower(), stop))

            self.response.out.write(
                PAGE_TEMPLATE % {
                    'title': stop + ': ' + description, 
                    'body': output.getvalue()}
                )
            return
        except (DeadlineExceededError, DeadlineExceededError2):
            redirect_url = '/stop/?number=%s&random=%s' % (stop, random.randint(1,100))
            self.redirect(redirect_url)
            logging.warn('Request preempted. Redirecting to %s' % redirect_url)

    def get_stop_details(self, stop):

        details = memcache.get(stop)
        if details is not None:
            logging.debug('Cache hit for stop %s' % stop)
            return details

        result = get_url('%s/index_svclist.aspx?stopcode=%s' % (SBS_SITE, stop))

        soup = BeautifulSoup(result)

        text = [c.strip() for c in soup.form.findAll(text=True) if c.strip()]
        description = []
        for t in text:
            if t.startswith('Please'):
                break
            description.append(t)

        if description:
            description = ', '.join(description)

        logging.info('stop %s description: %s' % (stop, description))

        services = []
        for link in soup('a'):
            services.append(unicode(link.string))

        logging.debug('for stop %s services are %s' % (stop, services))

        # save to memcache
        if not memcache.set(stop, 
                (description, services), time=604800): # 7 days
            logging.error('Failed saving cache for stop %s' % stop)
        else:
            logging.debug('Saved stop %s to cache' % stop)

        return (description, services)


    def get_timings(self, stop, service):

        if is_day_time() and service.endswith('N'):
            # Don't check night owl during day
            logging.warn('day time skip for %s' % service)
            return ('not operating now', 'no current prediction')

        cached = memcache.get('%s-%s' % (stop, service))
        if cached is not None:
            logging.debug('Cache hit for service %s at stop %s' \
                    % (service, stop))
            return cached

        result = get_url('%s/index_mobresult.aspx?stop=%s&svc=%s' \
                        % (SBS_SITE, stop, service))

        # Check if we are redirected
        if re.search(r'Object moved to', result, re.DOTALL):
            soup = BeautifulSoup(result)
            new_url = soup('a')[0]['href']
            logging.debug('new url: %s' % new_url)
            token = re.search(r'\(\w+?\)', new_url).group()
            logging.info('new token: %s' % token)
            result = get_url('%s/%s/index_mobresult.aspx?stop=%s&svc=%s' \
                            % (SBS_SITE, token, stop, service))
            #logging.info(result)

        x = re.search(r'Service\s+?%s<br.*?Next bus:\s+(?P<next>[\w\s\(\)]+)<br>.*?Subsequent bus:' \
                    '\s+(?P<subsequent>[\w\s\(\)]+)<br>' % service.lstrip('0'), result, re.DOTALL)

        if not x:
            logging.debug('failed to fetch info for service %s at stop %s' % (
                                service, stop))
            next, subsequent = ('retry', 'retry')
        else:
            next = x.group('next')
            subsequent = x.group('subsequent')

        # save to memcache
        if not memcache.set('%s-%s' % (stop, service), 
                            (next, subsequent), time=60): 
            logging.error('Failed saving cache for stop,svc %s,%s' \
                            % (stop, service))
        else:
            logging.debug('Saved cache for stop, svc %s, %s' % (stop, service))

        return (next, subsequent)

urls = [('/stop\/?', EndPoint)]

def main():
    #if os.environ['HTTP_HOST'].lower() in ('sbsnextbus.appspot.com',):
    #    logging.getLogger().setLevel(logging.INFO)
    #    debug = False
    #else:
    logging.getLogger().setLevel(logging.DEBUG)
    debug = True

    application = webapp.WSGIApplication(
          urls, debug=debug)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
