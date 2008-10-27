function init() {
    function mark_error() {
        document.getElementById('error').style.color = 'red';
    }
    var n_f = document.inputform.number;
    document.inputform.onsubmit = function() {
        var stop = n_f.value;
        if (stop.length != 5) {
            mark_error();
            return false;
        }
        var date = new Date();
        date.setTime(date.getTime()+(60*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
        document.cookie = "Stop="+stop+expires+"; path=/";
        return true;
    }
    var c = document.cookie.split(';');
    for (var i=0; i < c.length; i++) {
        if (c[i].indexOf('Stop') != -1) {
            n_f.value = c[i].split('=')[1];
        }
    }
    if (document.location.search.indexOf('error') > 0) {
        mark_error();
    }
    n_f.focus();
    n_f.select();
    /* Check if browser support XMLHttpRequest */
    if (window.XMLHttpRequest || window.ActiveXObject) {
        //n_f.innerHTML += '<input type="hidden" name="xhr" value="1" />';
        var input = document.createElement("input");
        input.name = 'xhr';
        input.type = 'hidden';
        input.value = '1';
        var t_form = document.getElementById('theform');
        t_form.appendChild(input);
        document.getElementById('debug').innerHTML = 'debug: browser supports ajax';
    } 
}
init();
