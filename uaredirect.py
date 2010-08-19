import logging
from google.appengine.ext.webapp import Request
import wsgiref.util 

class UserAgentRedirect(object):
    """Redirects capable browsers to xhr=1 version of page"""

    def __init__(self, subapp):
        self.subapp = subapp

    def __call__(self, environ, start_response):
        agent = environ.get("HTTP_USER_AGENT", "")
        request = Request(environ)

        logging.debug("agent: %s & path: %s & xhr: %s" % (agent, request.path, request.get("xhr")))

        if agent and request.path.startswith("/stop") and not request.get("xhr"):
            if "Firefox" in agent or "iPhone" in agent:
                new_url = request.url + "&xhr=1"
                start_response("301 Moved Permanently", 
                            [("Location", new_url), ('Content-Type', 'text/html')])
                return ["""<!DOCTYPE html> 
                <title>Update your bookmarks!</title> 
                <h1>Update your bookmarks!</h1>
                <p>This page has moved to <a href="%s">%s</a>""" % (new_url, new_url)]

        return self.subapp(environ, start_response)
