
page_body = """<!DOCTYPE html> 
        <head>
        <title>NextBus is no more</title> 
        <script type="text/javascript">
            var _gaq = _gaq || [];
            _gaq.push(['_setAccount', 'UA-1736551-5']);
            _gaq.push(['_trackPageview']);

            (function() {
                var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
                ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
                var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
            })();

            function recordOutboundLink(link, category, action) {
              _gaq.push(['_trackEvent', category, action]);
              setTimeout('document.location = "' + link.href + '"', 100);
            }
        </script>
        </head>
        <body>
        <h1>NextBus is no more</h1>
        <p>I've shut down this service for good. So long, and thanks for all the fish!</p>

        <p>For your bus timing needs, please try these sites:
        <ul><li><a href="http://www.publictransport.sg/mobile/" onClick="recordOutboundLink(this, 'Outbound Links', 'publictransport.sg');return false;">PublicTransport@SG</a></li>
        <li><a href="http://www.sbstransit.com.sg/mobileiris/"onClick="recordOutboundLink(this, 'Outbound Links', 'sbstransit.com.sg');return false;">SBSTransit iris</a></li>
        </ul>
        """

page_body_android = page_body + """<p>Or take a cab instead: try <a href="https://market.android.com/details?id=net.antrix.android.cabbiepro" onClick="recordOutboundLink(this, 'Outbound Links', 'cabbie-pro');return false;">Cabbie Pro for Android</a>."""

class EverythingGone(object):
    """Declare everything gone"""

    def __call__(self, environ, start_response):

        start_response("410 Gone", [('Content-Type', 'text/html')])

        user_agent = environ.get('HTTP_USER_AGENT', None)

        if user_agent and 'Android' in user_agent:
            return [page_body_android]

        return [page_body]

application = EverythingGone()
