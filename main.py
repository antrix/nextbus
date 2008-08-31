import wsgiref.handlers
import logging
import os
import re

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
try:
    from google.appengine.runtime import DeadlineExceededError
except:
    from google.appengine.runtime.apiproxy_errors import DeadlineExceededError

from BeautifulSoup import BeautifulSoup

SBS_SITE = 'http://www.sbstransit.com.sg/mobileiris'

def isvaliddomain():
    valid_list = ['sbsnextbus.appspot.com', 
             'localhost', 'localhost:9999', 'localhost:8080']
    if os.environ['HTTP_HOST'].lower() in valid_list:
        return True
    else:
        return False

def get_url(url):
    try:
        result = urlfetch.fetch(url)
        if result.status_code != 200:
            logging.error('Error code %s while fetching url: %s. Details: %s' % (
                result.status_code, url, result.content))
            raise Exception("Error fetching url")
        else:
            return result.content
    except urlfetch.Error, e:
        logging.error("Error fetching url %s" % url, exc_info=True)
        raise e

class EndPoint(webapp.RequestHandler):

    def get(self):
        if not isvaliddomain():
            self.error(503)
            self.response.out.write('You are not authorized to run this' +
                    ' application on the domain %s. Please visit sbsnextbus.appspot.com directly.'
                    % os.environ['HTTP_HOST'])
            return

        try:
            # Cast to int just to ensure we are getting a number
            stop = int(self.request.get('number'))
            stop = self.request.get('number')
        except ValueError:
            self.redirect('/')
            return

        try:
            # Fetch the bus services at this stop
            try:
                services = self.get_stop_details(stop)
            except:
                self.error(500)
                self.response.out.write('Error processing request. Please retry.')
                logging.error("Error getting stop details", exc_info=True)
                return

            self.response.out.write('<html><head><title>Services at stop %s' \
                    '</title></head><style type="text/css">body, td, th {font-size: smaller;}' \
                    '</style><body><p>Services at stop %s</p>' \
                    '<font><table border="0" cellpadding="2"><tr align="left"><th></th><th>Next</th>' \
                    '<th>Subsequent</th></tr>' % (stop, stop))
            for service in services:
                try:
                    next, subsequent = self.get_timings(stop, service)
                except DeadlineExceededError:
                    raise
                except:
                    next, subsequent = ('retry', 'retry')
                    logging.error("Error getting service details", exc_info=True)

                self.response.out.write('<tr><td><a href="%s/index_mobresult.aspx?' \
                        'stop=%s&svc=%s">%s</a></td><td>%s</td><td>%s</td></tr>' \
                        % (SBS_SITE, stop, service, service, next, subsequent))

            self.response.out.write('</table><br/><a href="http://%s/stop/?number=%s">' \
                    'Refresh</a></font></body></html>' % (os.environ['HTTP_HOST'].lower(),
                                                            stop))
            return
        except DeadlineExceededError:
            redirect_url = '/stop/?number=%s&random=%s' % (stop, random.randint(1,100))
            self.redirect(redirect_url)
            logging.info('Request preempted while processing %s for stop %s.' \
                    'Redirecting to %s' % service, stop, redirect_url)


    def get_stop_details(self, stop):

        details = memcache.get(stop)
        if details is not None:
            logging.debug('Cache hit for stop %s' % stop)
            return details

        result = get_url('%s/index_svclist.aspx?stopcode=%s' % (SBS_SITE, stop))

        soup = BeautifulSoup(result)

        services = []
        for link in soup('a'):
            services.append(unicode(link.string))

        logging.debug('for stop %s services are %s' % (stop, services))

        # save to memcache
        if not memcache.set(stop, services):
            logging.error('Failed saving cache for stop %s' % stop)
        else:
            logging.debug('Saved stop %s to cache' % stop)

        return services


    def get_timings(self, stop, service):

        cached = memcache.get('%s-%s' % (stop, service))
        if cached is not None:
            logging.debug('Cache hit for service %s at stop %s' \
                    % (service, stop))
            return cached

        result = get_url('%s/index_mobresult.aspx?stop=%s&svc=%s' \
                        % (SBS_SITE, stop, service))

        #logging.info(result)
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

        x = re.search(r'Next bus:\s+(?P<next>[\w\s\(\)]+)<br>.*?Subsequent bus:' \
                    '\s+(?P<subsequent>[\w\s\(\)]+)<br>', result, re.DOTALL)

        if not x:
            logging.debug('failed to fetch info for service %s at stop %s' % (
                                service, stop))
            return ('retry', 'retry')

        next = x.group('next')
        subsequent = x.group('subsequent')

        # save to memcache
        if not memcache.set('%s-%s' % (stop, service), 
                            (next, subsequent), time=60): 
            logging.error('Failed saving cache for stop,svc %s,%s' \
                            % (stop, service))
        else:
            logging.debug('Saved cache for stop,svc %s,%s' % (stop, service))

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
