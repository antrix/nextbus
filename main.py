import wsgiref.handlers
import logging
import os

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.runtime import DeadlineExceededError

from BeautifulSoup import BeautifulSoup

SBS_SITE = 'http://www.sbstransit.com.sg/mobileiris/'

def isvaliddomain():
    valid_list = ['nextbus.appspot.com', 
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
                    ' application on the domain %s. Please visit nextbus.appspot.com directly.'
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
                services, stop_description = self.get_stop_details(stop)
            except:
                self.error(500)
                self.response.out.write('Error processing request. Please retry.')
                logging.error("Error getting stop details", exc_info=True)
                return

            self.response.out.write('<html><head><title>Services at Stop %s' \
                    '</title></head><body><p>Stop %s <br/> %s</p>' \
                    '<table>' % (stop, stop, stop_description))
            for service in services:
                try:
                    next, subsequent = self.get_timings(stop, service)
                except:
                    self.error(500)
                    self.response.out.write('Error processing request. Please retry.')
                    logging.error("Error getting service details", exc_info=True)
                    return

                self.response.out.write('<tr><td>%s</td><td>%s</td>' \
                        '<td>%s</td></tr>' % (service, next, subsequent))

            self.response.out.write('</table></body></html>')
            return
        except DeadlineExceededError:
            redirect_url = '/stop/?number=%s&random=%s' % (stop, random.randint(1,100))
            self.redirect(redirect_url)
            logging.debug('Request preempted while processing %s for stop %s.' \
                    'Redirecting to %s' % service, stop, redirect_url)


    def get_stop_details(self, stop):

        details = memcache.get(stop)
        if details is not None:
            logging.info('Cache hit for stop %s' % stop)
            return (details[1:], details[0]) # (services, description)

        result = get_url('%s/index_svclist.aspx?stopcode=%s' % (SBS_SITE, stop))

        soup = BeautifulSoup(result)

        stop_description = ' '.join([unicode(x) for x in soup.font.contents])

        services = []
        for link in soup.table('a'):
            services.append(unicode(link.string))

        logging.debug('for stop %s at %s services are %s' % (
                    stop, stop_description, services))

        # save to memcache
        if not memcache.set(stop, (stop_description, services)):
            logging.error('Failed saving cache for stop %s' % stop)
        else:
            logging.debug('Saved stop %s to cache' % stop)

        return (services, stop_description)


    def get_timings(self, stop, service):

        next, subsequent = memcache.get('%s-%s' % (stop, service))
        if next is not None and subsequent is not None:
            logging.debug('Cache hit for service %s at stop %s' \
                    % (service, stop))
            return (next, subsequent)

        result = get_url('%s/index_mobresult.aspx?stop=%s&svc=%s' \
                        % (SBS_SITE, stop, service))

        x = re.search(r'Next bus:\s+(?P<next>[\w\s]+)<br>.*?Subsequent bus:' \
                    '\s+(?P<subsequent>[\w\s]+)</font>', html, re.DOTALL)

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
    application = webapp.WSGIApplication(
          urls, debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
