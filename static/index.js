function init() {
    function mark_error() {
        document.getElementById('error').style.color = 'red';
    }

    function createCookie(name,value,days) {
        if (days) {
            var date = new Date();
            date.setTime(date.getTime()+(days*24*60*60*1000));
            var expires = "; expires="+date.toGMTString();
        }
        else var expires = "";
        document.cookie = name+"="+value+expires+"; path=/";
    }

    function readCookie(name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i=0;i < ca.length;i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
        return null;
    }

    /* Check if browser support XMLHttpRequest */
    var xhr_f = null;
    if (window.XMLHttpRequest || window.ActiveXObject) {
        //n_f.innerHTML += '<input type="hidden" name="xhr" value="1" />';
        var t_form = document.getElementById('theform');
        var para = document.createElement('p');
        var text = document.createTextNode('Use advanced browser features?');
        xhr_f = document.createElement("input");
        xhr_f.type = 'checkbox';
        para.appendChild(text);
        para.appendChild(xhr_f);
        t_form.appendChild(para);
        xhr_f.name = 'xhr';
        xhr_f.value = '1';
        var initial = readCookie('xhr');
        if (initial) {
            xhr_f.checked = (initial == 'true') ? true : false;
        } else {
            xhr_f.checked = true;
        }
        document.getElementById('debug').innerHTML = 'debug: browser supports ajax';
    } 

    var n_f = document.inputform.number;
    var val = readCookie('Stop');
    if (val) {
        n_f.value = val;
    }

    document.inputform.onsubmit = function() {
        var stop = n_f.value;
        if (stop.length != 5) {
            mark_error();
            return false;
        }
        createCookie("Stop", stop, 30);
        if (xhr_f) {
            createCookie("xhr", xhr_f.checked);
        }
        createCookie("initialStop", "", -1);
        return true;
    }

    if (document.location.search.indexOf('error') > 0) {
        mark_error();
    }
    n_f.focus();
    n_f.select();
}
init();
