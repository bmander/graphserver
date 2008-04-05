var compute_url = "http://localhost/compute?";

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
// function computeJourney() : triggers the computation of the route
//
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

function computeJourney() {
	http_request = false;
	// Create an XMLHttp instance
	if (window.XMLHttpRequest) { // Mozilla, Safari,...
    	http_request = new XMLHttpRequest();
		if (http_request.overrideMimeType) {
			http_request.overrideMimeType('text/xml');
		}
	} else if (window.ActiveXObject) { // IE
		try {
			http_request = new ActiveXObject("Msxml2.XMLHTTP");
		} catch (e) {
			try {
				http_request = new ActiveXObject("Microsoft.XMLHTTP");
			} catch (e) {}
		}
	}

	if (!http_request) {
		alert('Error :(Could not create an XMLHttp instance');
		return false;
	}

	url="";
	// Set callback method
	http_request.onreadystatechange = showJourney;
	// Make asynchronous http request
	// url = compute_url + "from="+ document.getElementById('fromId').value + "&to="+ document.getElementById('toId').value;
	url = compute_url + "from="+ document.getElementById('from').value + "&to="+ document.getElementById('to').value;
	alert("La peticion se hara con:" + url);
	http_request.open('GET', url, true);
	http_request.send(null);
	return false;
}

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
// function showJourney() : shows the computed Journey
//
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

function showJourney() {
	if (http_request.readyState == 4) {
		if (http_request.status == 200) {
			alert('Response received');
//			var xmldoc = http_request.responseText;
//		  	document.getElementById('route').innerHTML = xmldoc;
			var xmldoc = http_request.responseXml;
			document.getElementById('route').innerHTML = "finished";
		} else {
			alert('There were problems with the journey planning server');
		}
	} else {
		document.getElementById('route').innerHTML = "computing journey...";
	}
}
