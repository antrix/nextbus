import logging
import re
from google.appengine.api import memcache

from BeautifulSoup import BeautifulSoup
from utils import get_url, is_day_time, SBS_SITE


def get_stop_details(stop):

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
        description.reverse()
        description = ', '.join(description)
        from titlecase import titlecase
        description = titlecase(description.lower())

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

def get_timings(stop, service):

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

    logging.info(result)
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

    x = re.search(r'Service\s+?%s<br.*?Next bus:\s+(?P<next>[\w\s\(\),]+)<br>.*?Subsequent bus:' \
                '\s+(?P<subsequent>[\w\s\(\),]+)<br>' % service.lstrip('0'), result, re.DOTALL)

    if not x:
        logging.debug('failed to fetch info for service %s at stop %s' % (
                            service, stop))
        raise Exception('Error fetching arrival times')

    next = x.group('next')
    subsequent = x.group('subsequent')

    # save to memcache
    # TODO: Reset memcache time to 1 minute before upload!
    if not memcache.set('%s-%s' % (stop, service), 
                        (next, subsequent), time=600): 
        logging.error('Failed saving cache for stop,svc %s,%s' \
                        % (stop, service))
    else:
        logging.debug('Saved cache for stop, svc %s, %s' % (stop, service))

    return (next, subsequent)

