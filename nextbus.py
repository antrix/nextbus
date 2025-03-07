import logging
import re
from google.appengine.api import memcache

from BeautifulSoup import BeautifulSoup
from utils import *
from sgbuses import all_stops
from lta import lta_stops

def get_stop_details(stop):
    """Given a bus stop number `stop`, this method
    returns a tuple (description, services) where
    `description` is a string describing `stop`
    and `services` is a list of service numbers
    operating at the `stop`"""

    this_stop = all_stops[stop]

    description = this_stop['description']

    logging.debug('stop %s description: %s' % (stop, description))

    only_sbs_services = True
    if stop in lta_stops:
        only_sbs_services = False

    services = []
    for service in this_stop['services']:
        if only_sbs_services:
            if service[1] == "SBS":
                services.append(service[0])
        else:
            services.append(service[0])

    logging.debug('for stop %s services are %s' % (stop, services))

    return (description, services)

def get_timings(stop, service):
    """Given a pair of `stop` number & `service` number, returns
    a tuple of string (next, subsequent) indicating the expected
    next & subsequent arrival time of `service` at `stop`"""

    if is_day_time() and (service.endswith('N') or service.startswith("NR")):
        # Don't check night owl during day
        logging.warn('day time skip for %s' % service)
        return ('not operating now', 'no current prediction')

    cached = memcache.get('%s-%s' % (stop, service))
    if cached is not None:
        logging.debug('Cache hit for service %s at stop %s' \
                % (service, stop))
        return cached

    if stop in lta_stops:
        return _get_timings_lta(stop, service)
    else:
        return ("blocked", "blocked")
        #return _get_timings_sbs(stop, service)

sbs_regex = re.compile(r"<td>Svc:</td><td>(?P<svc>.*?)</td></tr><tr><td>next bus:</td><td>(?P<next>.*?)</td>.*?subsequent bus:</td><td>(?P<subsequent>.*?)</td>", re.IGNORECASE|re.DOTALL)

def _get_timings_sbs(stop, service):

    # return ("blocked", "blocked") # Till we get un-blocked by SBS!

    result = get_url("%s/busstop.aspx?svc=%s&stop=%s" % (SBS_SITE, service, stop), deadline=3)

    x = sbs_regex.finditer(result)

    if not x:
        logging.error('parsing result page failed for service %s at stop %s' % (
                            service, stop))
        logging.error(result)
        raise Exception('Error fetching arrival times')

    arrv, subs = 'retry', 'retry'

    for p in x:
        svc = p.group('svc').strip()
        arriving = p.group('next').strip()
        subsequent = p.group('subsequent').strip()

        # To make service numbers compatible w/ SBS, we'll
        # pad them with 0, i.e. '002' instead of '2'
        svc = svc.zfill(3)

        logging.debug("svc, arriving, subsequent: %s %s %s" % (svc, arriving, subsequent))

        if svc == service:
            arrv, subs = arriving, subsequent

        # save to memcache
        if not memcache.set('%s-%s' % (stop, svc), 
                            (arriving, subsequent), time=60): 
            logging.error('Failed saving cache for stop,svc %s,%s' \
                            % (stop, svc))
        else:
            logging.debug('Saved cache for stop, svc %s, %s' % (stop, svc))

    return (arrv, subs)

def _get_timings_lta(stop, service):

    stop = stop.strip()
    service = service.strip()

    result = get_url('%s?bus_stop=%s&bus_service=&submit=Submit' % (LTA_SITE, stop))

    soup = BeautifulSoup(result)
    #logging.debug(soup)

    is_wab = lambda(val): 'handicapped' in val

    timings = {}
    for row in soup.table.findAll('tr'):
        cols = row.findAll('td')
        if len(cols) != 3: continue # line breaks
        if 'Bus' in cols[0].string: continue # Header
        svc = cols[0].string.strip()
        # To make service numbers compatible w/ SBS, we'll
        # pad them with 0, i.e. '002' instead of '2'
        svc = svc.zfill(3)

        if cols[1].contents:
            arrv = cols[1].contents[0].strip().replace('&nbsp;', '')
            if cols[1].find('img', src=is_wab):
                arrv = arrv + ' (WAB)'
        else:
            arrv = None

        if cols[2].contents:
            subsequent = cols[2].contents[0].strip().replace('&nbsp;', '')
            if cols[2].find('img', src=is_wab):
                subsequent = subsequent + ' (WAB)'
        else:
            subsequent = None

        if arrv and subsequent:
            timings[svc] = (arrv, subsequent)
            # save to memcache
            if not memcache.set('%s-%s' % (stop, svc), (arrv, subsequent), time=60): 
                logging.error('LTA: Failed saving cache for stop,svc %s,%s' \
                                % (stop, svc))
            else:
                logging.debug('LTA: Saved cache for stop, svc %s, %s' % (stop, svc))

    return timings[service]

