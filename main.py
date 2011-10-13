from google.appengine.ext.webapp.util import run_wsgi_app

class EverythingGone(object):
    """Declare everything gone"""

    def __call__(self, environ, start_response):

        start_response("410 Gone", [('Content-Type', 'text/html')])
        return ["""<!DOCTYPE html> 
        <title>NextBus is no more</title> 
        <h1>NextBus is no more</h1>
        <p>I've shut down this service for good. So long, and thanks for all the fish!"""]

def main():
    application = EverythingGone()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
