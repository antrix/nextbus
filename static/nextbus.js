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
            $('#stop-description').text('fetching stop description...');
            $.getJSON(NextBus.urlFor(stop), function(data) {
                if (data.code != 200) {
                    $('#error').text(data.message ? data.message : 'Error fetching data.');
                    $('#stop-description').text('');
                } else if (data.services.length < 1) {
                    $('#error').text("Hmm.. didn't find any services for this stop.");
                } else {
                    $('#stop-description').text(data.description);
                    NextBus.currentStop = stop;
                    NextBus.currentServices = data.services;
                    NextBus.updateAllTimings();
                }
            });
        },

    updateTiming:
        function(service) {
            var stop = NextBus.currentStop;
            var row = $('#'+service);
            var td_n = row.find('.next');
            var td_s = row.find('.subsequent'); 
            td_n.html('...'); td_s.html('...');
            $.getJSON(NextBus.urlFor(stop, service), function(data) {
                var n, s;
                if (data.code != 200) {
                    n = 'retry';
                    s = 'retry';
                } else {
                    n = data.arrivals[service].next;
                    s = data.arrivals[service].subsequent;
                }
                //alert('for ' + service + ', n: '+n+', s: '+s);
                td_n.html(n);
                td_s.html(s);
            });
        },

    updateAllTimings:
        function() {
            stop = NextBus.currentStop;
            services = NextBus.currentServices;
            $.each(services, function(i, service) {
                var row = $('#'+service);
                if (row.length == 0) {
                    row = $('<tr></tr>');
                    row.attr('id', service);
                    row.appendTo('#grid tbody');
                }
                var a = $('<a href="'+NextBus.sbsUrlFor(stop, service)+'">'+service+'</a>')
                            .click( function() {
                                NextBus.updateTiming(service);
                                return false;
                            });
                var td = $('<td></td>').append(a);
                row.html('');
                row.append(td);
                row.append('<td class="next"></td><td class="subsequent"></td>');
                NextBus.updateTiming(service);
            });
            $('#grid').show();
        }
}

$(document).ready(function() {
    stop = $('#stop-number').text();
    $('#refresh-link').click(function() {
            NextBus.updateAllTimings();
            return false;
        });
    NextBus.fetchStopInfo(stop);
}); /* End $(document).ready() block */

