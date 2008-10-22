var NextBus = NextBus ? NextBus : {

    currentStop: '',
    currentServices: [],
    urlFor: 
        function(stop, service) {
            return '/api/v1/' + stop + ( service ? '/' + service : '') + '/?callback=?'
        },

    sbsUrlFor: 
        function(stop, service) {
            return 'http://www.sbstransit.com.sg/mobileiris/index_mobresult.aspx?stop='+stop+'&svc='+service
        },

    fetchStopInfo:
        function(stop) {
            $.getJSON(NextBus.urlFor(stop), function(data) {
                if (data.code != 200) {
                    $('#error').text(data.message ? data.message : 'Error fetching data.');
                } else if (data.services.length < 1) {
                    $('#error').text("Hmm.. didn't find any services for this stop.");
                } else {
                    $('#stop-description').text(data.description);
                    NextBus.currentStop = stop;
                    NextBus.currentServices = data.services;
                    NextBus.updateTimings();
                }
            });
        },

    updateTimings:
        function() {
            stop = NextBus.currentStop;
            services = NextBus.currentServices;
            $('#grid').hide();
            $('#grid tbody').html('');
            $.each(services, function(i, service) {
                var row = $('<tr id="'+service+'></tr>');
                row.html('<td><a href="'+NextBus.sbsUrlFor(stop, service)+'">'+
                            service + '</a></td><td class="next"></td><td class="subsequent"></td>');
                row.appendTo('#grid tbody');
                $.getJSON(NextBus.urlFor(stop, service), function(data) {
                    var n, s;
                    if (data.code != 200) {
                        n = 'retry';
                        s = 'retry';
                    } else {
                        n = data.arrivals[service].next;
                        s = data.arrivals[service].subsequent;
                    }
                    row.children('.next').html(n);
                    row.children('.subsequent').html(s);
                });
            });
            $('#grid').show();
        }
}

$(document).ready(function() {
    stop = $('#stop-number').text();
    $('#refresh-link').click(function() {
            NextBus.updateTimings();
            return false;
        });
    NextBus.fetchStopInfo(stop);
}); /* End $(document).ready() block */

