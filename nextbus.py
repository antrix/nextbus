import logging
import re
from google.appengine.api import memcache
from django.utils import simplejson as json

from BeautifulSoup import BeautifulSoup
from utils import *
from lta import lta_stops

def get_stop_details(stop):

    details = memcache.get(stop)
    if details is not None:
        logging.debug('Cache hit for stop %s' % stop)
        return details

    if stop in lta_stops:
        return get_stop_details_lta(stop)
    else:
        return get_stop_details_sbs(stop)

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

    if stop in lta_stops:
        return get_stop_details_lta(stop, service)
    else:
        return get_timings_sbs(stop, service)

def get_stop_details_sbs(stop):

    all_stops = json.load(open('sgbuses.json'))

    this_stop = all_stops[stop]

    description = this_stop['description']

    logging.debug('stop %s description: %s' % (stop, description))

    services = []
    for service in this_stop['services']:
        if service[1] == "SBS":
            services.append(service[0])

    logging.debug('for stop %s services are %s' % (stop, services))

    # save to memcache
    if not memcache.set(stop, 
            (description, services), time=604800): # 7 days
        logging.error('Failed saving cache for stop %s' % stop)
    else:
        logging.debug('Saved stop %s to cache' % stop)

    return (description, services)

def get_timings_sbs(stop, service):

    if USE_SBS_PROXY:
        result = get_url(SBS_SITE_PROXY() + '%2Findex_mobresult.aspx%3Fstop%3D' + stop + '%26svc%3D'+ service)
    else:
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
        if USE_SBS_PROXY:
            result = get_url(SBS_SITE_PROXY() + '%2F' + token + '%2Findex_mobresult.aspx%3Fstop%3D' + stop + '%26svc%3D'+ service)
        else:
            result = get_url('%s/%s/index_mobresult.aspx?stop=%s&svc=%s' \
                            % (SBS_SITE, token, stop, service))
        #logging.info(result)

    x = re.search(r'Service\s+?%s<br.*?Next bus:\s+(?P<next>[\w\s\(\),]+)<br>.*?Subsequent bus:' \
                '\s+(?P<subsequent>[\w\s\(\),]+)<br>' % service.lstrip('0'), result, re.DOTALL)

    if not x:
        logging.error('parsing result page failed for service %s at stop %s' % (
                            service, stop))
        logging.error(result)
        raise Exception('Error fetching arrival times')

    next = x.group('next')
    subsequent = x.group('subsequent')

    # save to memcache
    # TODO: Reset memcache time to 1 minute before upload!
    if not memcache.set('%s-%s' % (stop, service), 
                        (next, subsequent), time=60): 
        logging.error('Failed saving cache for stop,svc %s,%s' \
                        % (stop, service))
    else:
        logging.debug('Saved cache for stop, svc %s, %s' % (stop, service))

    return (next, subsequent)

def get_stop_details_lta(stop, req_service=None):

    description = lta_stops[stop]

    result = get_url('%s?bus_stop=%s&bus_service=&submit=Submit' % (LTA_SITE, stop))

    soup = BeautifulSoup(result)
    #logging.debug(soup)

    services = []
    timings = {}

    is_wab = lambda(val): 'handicapped' in val

    for row in soup.table.findAll('tr'):
        cols = row.findAll('td')
        if len(cols) != 3: continue # line breaks
        if 'Bus' in cols[0].string: continue # Header
        service = cols[0].string.strip()
        services.append(service)
        next = cols[1].contents[0].strip().replace('&nbsp;', '')
        if cols[1].find('img', src=is_wab):
            next = next + ' (WAB)'
        subsequent = cols[2].contents[0].strip().replace('&nbsp;', '')
        if cols[2].find('img', src=is_wab):
            subsequent = subsequent + ' (WAB)'
        timings[service] = (next, subsequent)
        # save to memcache
        if not memcache.set('%s-%s' % (stop, service), 
                            (next, subsequent), time=60): 
            logging.error('LTA: Failed saving cache for stop,svc %s,%s' \
                            % (stop, service))
        else:
            logging.debug('LTA: Saved cache for stop, svc %s, %s' % (stop, service))


    logging.debug('LTA: for stop %s services are %s' % (stop, services))

    # save to memcache
    if not memcache.set(stop, 
            (description, services), time=604800): # 7 days
        logging.error('LTA: Failed saving cache for stop %s' % stop)
    else:
        logging.debug('LTA: Saved stop %s to cache' % stop)

    if req_service:
        return timings[req_service]
    else:
        return (description, services)

