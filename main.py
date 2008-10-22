import wsgiref.handlers
from datetime import timedelta, tzinfo, datetime, time
import logging
import os
import random
import re
import StringIO

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
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
from django.utils import simplejson as json

# My imports
from utils import *
import nextbus

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

def isvaliddomain():
    valid_list = ['sbsnextbus.appspot.com', 
             'localhost', 'localhost:9999', 'localhost:8080']
    host = os.environ['HTTP_HOST'].lower()
    for valid_host in valid_list:
        if host.endswith(valid_host):
            return True
    return False

class APIEndPoint(webapp.RequestHandler):

    def get(self, stop, service=None):
        try:
            stop_details = nextbus.get_stop_details(stop)
            response = {'code': 200, 'stop': stop}
            response['description'] = stop_details[0]
            response['services'] = stop_details[1]
            if service:
                if service not in stop_details[1]:
                    response['code'] = 404
                    response['message'] = 'No such service (%s) for stop %s' % (service, stop)
                else:
                    next, subsequent = nextbus.get_timings(stop, service)
                    response['arrivals'] = {service: {'next': next, 'subsequent': subsequent}}
        except Exception, e:
            if isinstance(e, HTTPError) and e.code == 404:
                self.error(404)
                response = {'code': 404, 'message': 'Stop %s not found.' % stop}
            else:
                self.error(500)
                response = {'code': 500, 'message': 'Something bad happened. Please retry.'}
                if not isinstance(e, HTTPError):
                    logging.error("Error getting stop details", exc_info=True)

        response = json.dumps(response, indent=2)
        json_callback = self.request.get('callback').encode('utf-8')
        if json_callback:
            self.response.out.write('%s(%s);' % (json_callback, response))
        else:
            self.response.out.write(response)
        return

class WebEndPoint(webapp.RequestHandler):

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
            details = nextbus.get_stop_details(stop)
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
                    next, subsequent = nextbus.get_timings(stop, service)
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


urls = [(r'/stop/?', WebEndPoint),
        (r'/api/v1/(\d{5})/$', APIEndPoint),
        (r'/api/v1/(\d{5})/(\w+)/$', APIEndPoint)]

def main():
    #if os.environ['HTTP_HOST'].lower() in ('sbsnextbus.appspot.com',):
    #    logging.getLogger().setLevel(logging.INFO)
    #    debug = False
    #else:
    logging.getLogger().setLevel(logging.DEBUG)
    debug = True

    application = webapp.WSGIApplication(
          urls, debug=debug)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
