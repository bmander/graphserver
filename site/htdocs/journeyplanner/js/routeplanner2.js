var mapstraction;
var peticionGeoDirecta = "myOSMNameFinder?";
var peticionId = "MyOSMIdFinder?";
var peticionRuta = "MyOSMRouteFinder?";
var peticionGeoInversa = "MyInverseOSMIdFinder?";
var idOrigenSeleccionado = false;
var idDestinoSeleccionado = false;
//var esperarSeleccion = false;

var marcadorOrigen = null;
var marcadorDestino = null;

var origenFinal = "";
var destinoFinal = "";

var streetIni;
var ORIGIN = 0;
var DESTINY = 1;

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
// function PeticionRuta() : activada cada vez q se quiere realizar una busqueda
//
//
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

function PeticionRuta()
{
	  // En primer lugar se obtendran los identificadores para cada calle en texto
	  if (!idOrigenSeleccionado)
		 PeticionNombres(1);
 	  if (!idDestinoSeleccionado)
    	 PeticionNombres(2);

 	  if ((!idOrigenSeleccionado)||(!idDestinoSeleccionado)) // Si es necesario esperar mas input del usuario no se hace la peticion
	 	return;

	  http_request3 = false;

   	   if (window.XMLHttpRequest) { // Mozilla, Safari,...
     	 http_request3 = new XMLHttpRequest();
      	 if (http_request3.overrideMimeType) {
            http_request3.overrideMimeType('text/xml');
           // Ver nota sobre esta linea al final
         }
       } else if (window.ActiveXObject) { // IE
       		try {
              http_request3 = new ActiveXObject("Msxml2.XMLHTTP");
       		} catch (e) {
               try {
               	 http_request3 = new ActiveXObject("Microsoft.XMLHTTP");
	           } catch (e) {}
            }
      }
	   if (!http_request3) {
       alert('Falla :( No es posible crear una instancia XMLHTTP');
       return false;
      }

	url="";
	http_request3.onreadystatechange = pideRuta;
	url = peticionRuta + "origen="+ document.getElementById('fromId').value + "&destino="+ document.getElementById('toId').value;
	//alert("La peticion se hara con:" + url);
	http_request3.open('GET', url, true);
	http_request3.send(null);
	return false;
}

	/*Esta es la funcion q muestra los resultados una vez que han sido realizados todos los
	pasos previos*/
	function pideRuta()
	{
		if (http_request3.readyState == 4)
		{
            if (http_request3.status == 200)
            {
            	document.getElementById('route').innerHTML = "";
            	var xmldoc = http_request3.responseXML;
           		var listaEdges = xmldoc.childNodes[0].getElementsByTagName('edge');
		 	//  var streetIni = listaEdges[0].childNodes[0];
	   		/*  var nomIni = streetOrTrip.getAttribute('name');
			 	var nombreIni = nomIni.substring(0, nomIni.indexOf('('));
			 	var longitudIni = parseFloat(streetOrTrip.getAttribute('length'));
   		 	 */

		  	//	var rutaString = "Iinicie la ruta en la "  calle " + nombreIni +". Siga en ella";
		  		var rutaString = "";
  			    var longitud=0;
  			    var ultimo = 'street';
  			    var ultimoNombre = '';
  				for (var i = 0; i< listaEdges.length; i++)
		  		{
					var streetOrTrip = listaEdges[i].childNodes[0];

					if (streetOrTrip.nodeName == 'street')
   		 	    	{
						if (ultimo == 'street')
						{
							var nomAux = streetOrTrip.getAttribute('name');
							longitud = longitud + parseFloat(streetOrTrip.getAttribute('length')) ;
							if(nomAux != ultimoNombre)
							{
								rutaString = rutaString + " " + nomAux + " durante " + parseInt(Math.ceil(longitud)) + " metros.<br/>" ;
								longitud =0;
								ultimoNombre = nomAux;
							}
							ultimo = 'street';
						}
						else if (ultimo == 'triphop')
						{
							var nomAux = streetOrTrip.getAttribute('name');
							if(nomAux == ultimoNombre)
							longitud = parseFloat(streetOrTrip.getAttribute('length'));
							rutaString = rutaString + "Baje y continue por " + nomAux + " durante " + parseInt(Math.ceil(longitud)) + " metros.<br/>" ;
							ultimo = "street";
						}
						ultimo = 'street'
					}
					else if (streetOrTrip.nodeName == 'triphop')
   		 	   	 	{
	   		 	   	 	if (ultimo == 'street')
						{
			   				var nomAux = streetOrTrip.getAttribute('trip_id');
							var longitud = parseFloat(streetOrTrip.getAttribute('transit')) ;
							rutaString = rutaString + " Suba en la parada parada " + nomAux + " durante " + longitud + " metros. <br/>" ;
							ultimo = 'triphop'
   						}
   						else if (ultimo == 'triphop')
						{
							var nomAux = streetOrTrip.getAttribute('trip_id');
							var longitud = parseFloat(streetOrTrip.getAttribute('transit')) ;
							rutaString = rutaString + " Pase por la parada " + nomAux + " durante " + longitud + " metros. <br/>" ;
							ultimo = 'triphop'
						}

   		 	   	 	}
   		 	   	}

/*				var nomAux = street.getAttribute('name');
    			var nombreAux = nomAux.substring(0, nomAux.indexOf('('));
				var longitud = parseFloat(street.getAttribute('length')) ;
			    if(nombreIni == nombreAux )
			 	{
				  	longitudIni = longitudIni + longitud ;
				}
				if(nombreIni != nombreAux )
				{
			  		rutaString = rutaString + " durante " + parseInt(Math.ceil(longitudIni)) + " metros. <br/>Continue por " + nombreAux;
				    nombreIni = nombreAux;
				    longitudIni = longitud;
				}
		  	}  	*/

		  	rutaFinal = rutaString;// + "durante " + parseInt(Math.ceil(longitudIni)) + " metros.<br/> Ha llegado a su destino.";
  			var oldRouteContents = document.getElementById('route').innerHTML;
		  	document.getElementById('route').innerHTML = oldRouteContents + "<h3>La ruta mas corta es: <br/></h3><p>" + rutaFinal + "</p>";
		  	idOrigenSeleccionado = false;
		  	idDestinoSeleccionado = false;
        }
        else
        {
            alert('Hubo problemas con la peticion.');
        }
     }
  }


  function procesaRutaCoche(xmldoc)
  {
 	var listaEdges = xmldoc.childNodes[0].getElementsByTagName('edge');
  	var streetIni = listaEdges[0].childNodes[0];
    var nomIni = streetOrTrip.getAttribute('name');
	var nombreIni = nomIni.substring(0, nomIni.indexOf('('));
	var longitudIni = parseFloat(streetOrTrip.getAttribute('length'));
	var rutaString = "Iinicie la ruta en " + nombreIni + ". Siga en ella";

	for (var i = 0; i< listaEdges.length; i++)
	{
		var street = listaEdges[i].childNodes[0];
		var nomAux = streetOrTrip.getAttribute('name');
    	var nombreAux = nomAux.substring(0, nomAux.indexOf('('));
		var longitud = parseFloat(streetOrTrip.getAttribute('length')) ;

		if(nombreIni == nombreAux )
		{
		  	longitudIni = longitudIni + longitud ;
		}
		if(nombreIni != nombreAux )
		{
			rutaString = rutaString + " durante " + parseInt(Math.ceil(longitudIni)) + " metros. <br/>Continue por " + nombreAux;
		    nombreIni = nombreAux;
		    longitudIni = longitud;
		}
    }
   	rutaFinal = rutaString + "durante " + parseInt(Math.ceil(longitudIni)) + " metros.<br/> Ha llegado a su destino.";
	var oldRouteContents = document.getElementById('route').innerHTML;
  	document.getElementById('route').innerHTML = oldRouteContents + "<h3>La ruta mas corta es: <br/></h3><p>" + rutaFinal + "</p>";
  	idOrigenSeleccionado = false;
  	idDestinoSeleccionado = false;

  }

  function procesaRutaBus(xmldoc)
  {
	var listaEdges = xmldoc.childNodes[0].getElementsByTagName('edge');


  }

  function procesaRutaMixta(xmldoc)
  {


  }


////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
// function PeticionNombres(param) :
//
//
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

function PeticionNombres(param) {

    http_request = false;

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
       alert('Falla :( No es posible crear una instancia XMLHTTP');
       return false;
    }
    url="";
    if (param==1)
 	{
 		document.getElementById('lista1').innerHTML ="";
		http_request.onreadystatechange = alertContents1;
		url = peticionGeoDirecta + "origen="+ document.getElementById('from').value ;
	}
	else  if (param==2)
	{
	 	document.getElementById('lista2').innerHTML ="";
		http_request.onreadystatechange = alertContents2;
		url = peticionGeoDirecta + "destino="+ document.getElementById("to").value;
	}
    http_request.open('GET', url, false);
    http_request.send(null);
	return false;
}

 	function alertContents1()
 	{
        if (http_request.readyState == 4) {
            if (http_request.status == 200) {
            	var xmldoc = http_request.responseXML;
				parseXMLNombres(xmldoc, 1);
            }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
    }

    function alertContents2()
    {
        if (http_request.readyState == 4) {
            if (http_request.status == 200)
            {
          	    var xmldoc = http_request.responseXML;
				parseXMLNombres(xmldoc,2);
            }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
    }

    function parseXMLNombres(xml, param2)
    {
	  var cont =0;
	  var divLista1 = document.getElementById('lista1');
 	  var divLista2 = document.getElementById('lista2');
 	  var divLista;
	  var contenidoLista;
	  var sugestedName;
	  var sugestedId;

	  if(param2 ==1)
     	 divLista = divLista1;
	  else if(param2 ==2)
     	divLista = divLista2;

	  var listContents ="";


      var nodeList1 =  xml.childNodes[0].getElementsByTagName('named');
	  for (var i = 0; i <= nodeList1.length; i++)
	  {
		  try{
	   		  var named = nodeList1[i];
		 	  var tipo = named.getAttribute('type');
			  var categoria = named.getAttribute('category');

		  	if (( tipo == 'way') && (categoria == 'highway'))
		  	{
 		  	 	cont = cont +1;
 		  	 	sugestedName = named.getAttribute('name');
		  		sugestedId = named.getAttribute('id');
		  		sugestedCity = named.getAttribute('is_in');

		  		if (sugestedCity == null)
		  		{
		  			sugestedCity = named.getElementsByTagName('nearestplaces')[0].childNodes[0].getAttribute('is_in');
		  			if (sugestedCity == null)
		  			{
		  				sugestedCity = named.getElementsByTagName('nearestplaces')[0].childNodes[0].getAttribute('name');
		  			}
			  	}
 	  	  	    if(param2 ==1)
			    {
			  	 	listContents = listContents + "<li><a onclick='rellena1(\""+ sugestedName +"\" , \""+ sugestedId +"\")'>" + sugestedName + ", " + sugestedCity + "</a></li>";
			  	 	//esperarSeleccion = true;
				}
	  		    else if(param2 ==2)
			    {
			  	 	listContents = listContents + "<li><a onclick='rellena2(\""+ sugestedName +"\" , \""+ sugestedId +"\")'>" + sugestedName + ", " + sugestedCity + "</a></li>";
			  	 //	esperarSeleccion = true;
			 	}
		 	}
		 }
		 catch (e)
		 {
		 // alert('peta');
		 }
	  }
	  // Si al acabar el for tan solo ha habido 1 resultado, hay q realizar la peticion
	  // del identificador
	  if (cont ==0)
	  {
	  	alert('No se encontrar la localizacion para esa calle');
	  }
	  if (cont ==1)
	  {
	  	if (param2 ==1)
	  	{
		 	rellena1(sugestedName, sugestedId);
			idOrigenSeleccionado = true;
		}
		else
			rellena2(sugestedName, sugestedId);
			idDestinoSeleccionado = true;
	  }
	  else
	  {
		 divLista.innerHTML = "<ul>" + listContents + "</ul>";
	  }

    }

    function rellena1(cadena, id)
    {
    	document.getElementById('from').value= cadena;
    	document.getElementById('lista1').innerHTML ="";
    	peticionIds(id,1);
    	idOrigenSeleccionado = true;
    	PeticionRuta();
	}

	function rellena2(cadena, id)
    {
    	document.getElementById('to').value= cadena;
    	document.getElementById('lista2').innerHTML ="";
    	peticionIds(id,2);
    	idDestinoSeleccionado = true;
    	PeticionRuta();
	}


	function rellena1b(cadena, id)
    {
    	document.getElementById('from').value= cadena;
    	document.getElementById('lista1').innerHTML ="";
    	peticionIds(id,1);
    	idOrigenSeleccionado = true;
    //	PeticionRuta();
	}

	function rellena2b(cadena, id)
    {
    	document.getElementById('to').value= cadena;
    	document.getElementById('lista2').innerHTML ="";
    	peticionIds(id,2);
    	idDestinoSeleccionado = true;
//    	PeticionRuta();
	}


	function peticionIds(id, param) {

	   http_request2 = false;

	   if (window.XMLHttpRequest) { // Mozilla, Safari,...
    	  http_request2 = new XMLHttpRequest();
       if (http_request2.overrideMimeType) {
          http_request2.overrideMimeType('text/xml');
          // Ver nota sobre esta linea al final
        }
   		} else if (window.ActiveXObject) { // IE
       try {
          http_request2 = new ActiveXObject("Msxml2.XMLHTTP");
       } catch (e) {
           try {
               http_request2 = new ActiveXObject("Microsoft.XMLHTTP");
           } catch (e) {}
       }
   }

   if (!http_request2) {
       alert('Falla :( No es posible crear una instancia XMLHTTP');
       return false;
   }

   url="";
   if (param==1)
	{
		http_request2.onreadystatechange = respuestaOSMApi1;
		url = peticionId + "origen="+ id ;
	}
	else  if (param==2)
	{
		http_request2.onreadystatechange = respuestaOSMApi2;
		url = peticionId + "destino="+ id;
	}

    http_request2.open('GET', url, false);
    http_request2.send(null);
	return false;

}

	function respuestaOSMApi1()
    {
	  if (http_request2.readyState == 4) {
            if (http_request2.status == 200) {

            // var divLista = document.getElementById('listas');
            // Mostrar todos los elementos en el div de datos
            	var xmldoc2 = http_request2.responseXML;
				//alert(http_request2.responseText);
				procesaRespuesta(xmldoc2, 1);
            }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
	}

	function respuestaOSMApi2()
    {
	  if (http_request2.readyState == 4) {
            if (http_request2.status == 200) {

            // var divLista = document.getElementById('listas');
            // Mostrar todos los elementos en el div de datos
            	var xmldoc2 = http_request2.responseXML;
				//alert(http_request2.responseText);
				procesaRespuesta(xmldoc2, 2);
            }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
	}


	function procesaRespuesta(xml, parametro)
	{

		var node =  xml.childNodes[0].getElementsByTagName('node')[0];
		var idNode = node.getAttribute('id');
		var latNode = node.getAttribute('lat');
		var lonNode = node.getAttribute('lon');

		var el = document.createElement('h1');
		if( parametro == 1)
		{
			document.getElementById('fromId').value= idNode;
			origenFinal = idNode;
			var texto = document.getElementById('from').value;
			el.appendChild( document.createTextNode('Origen: ' + texto ));
//			addMarkerAtLonLat (lonNode, latNode);
			addMarkerAtLonLat (lonNode, latNode, ORIGIN);
			/*
			var ll = new LatLonPoint( latNode, lonNode );

			mapstraction.removeMarker(marcadorOrigen);

  			marcadorOrigen = new Marker(ll);
	    	marcadorOrigen.setInfoBubble(el);
		    mapstraction.addMarker( marcadorOrigen );
		    mapstraction.setCenterAndZoom(ll, 15);
		    */
		}
		else if( parametro == 2)
		{
			document.getElementById('toId').value= idNode;
			destinoFinal = idNode;
			var texto = document.getElementById('to').value;
			el.appendChild( document.createTextNode('Destino: ' + texto  ));
//			addMarkerAtLonLat (lonNode, latNode);
			addMarkerAtLonLat (lonNode, latNode, DESTINY);
			/*
			var ll = new LatLonPoint( latNode, lonNode );

			mapstraction.removeMarker(marcadorDestino);

  			marcadorDestino = new Marker(ll);
	    	marcadorDestino.setInfoBubble(el);
		    mapstraction.addMarker( marcadorDestino );
		    mapstraction.setCenterAndZoom(ll, 15);
		    */
		}

	}

////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////


	function clickando(point)
	{
		// Con las coordenadas de latitud longitud obtendremos
   		// el nodo OSM mas cercano a la zona del click
    	var latitud =point.lat;
    	var longitud = point.lon;
    	var valor = document.getElementById('fromRadio').checked;
    //	alert(valor);
    	if(valor)
	    	PeticionIdsFromLatLon(1, latitud, longitud);
	    else
		    PeticionIdsFromLatLon(2, latitud, longitud);
		/*else
		{
			clearResults();
			PeticionIdsFromLatLon(1, latitud, longitud);
		} */
   	//	var ll = new LatLonPoint( point.lat, point.lon );
  	//	var marker = new Marker(ll);
  	//  mapstraction.addMarker( marker );
	}


	function clearResults()
	{
		mapstraction.removeMarker(marcadorOrigen);
		mapstraction.removeMarker(marcadorDestino);
		idOrigenSeleccionado = false;
		idDestinoSeleccionado = false;
		document.getElementById('from').value="";
		document.getElementById('fromId').value="";
		document.getElementById('to').value="";
		document.getElementById('toId').value="";
	}

	function PeticionIdsFromLatLon(param, lati, long) {

   	http_request4 = false;

    if (window.XMLHttpRequest) { // Mozilla, Safari,...
      http_request4 = new XMLHttpRequest();
      if (http_request4.overrideMimeType) {
          http_request4.overrideMimeType('text/xml');
          // Ver nota sobre esta linea al final
      }
    } else if (window.ActiveXObject) { // IE
       try {
          http_request4 = new ActiveXObject("Msxml2.XMLHTTP");
       } catch (e) {
           try {
               http_request4 = new ActiveXObject("Microsoft.XMLHTTP");
           } catch (e) {}
       }
   }

   if (!http_request4) {
       alert('Falla :( No es posible crear una instancia XMLHTTP');
       return false;
   }

    url="";
    if (param==1)
 	{
		http_request4.onreadystatechange = rellenaOSMIdOrigen;
	}
	else  if (param==2)
	{
		http_request4.onreadystatechange = rellenaOSMIdDestino;
	}
    url = peticionGeoInversa + "lat="+ lati + "&lon=" + long ;
    http_request4.open('GET', url, true);
    http_request4.send(null);
	return false;
}

	function rellenaOSMIdOrigen()
	{
	    if (http_request4.readyState == 4) {
            if (http_request4.status == 200) {
            	var xmldoc = http_request4.responseXML;
				//alert(http_request4.responseText);
				parseaXMLIds(http_request4.responseXML,1);

		    }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
	}

	function rellenaOSMIdDestino()
	{
	    if (http_request4.readyState == 4) {
            if (http_request4.status == 200) {
            	var xmldoc = http_request4.responseXML;
			//	alert(http_request4.responseText);
				parseaXMLIds(http_request4.responseXML,2);
            }
            else
            {
                alert('Hubo problemas con la peticion.');
            }
        }
	}

	function parseaXMLIds(xmldoc, param)
	{
		var listaNamed = xmldoc.childNodes[0].getElementsByTagName('named');
		// Desde 0 (el primer elemento es 0)
		for (var i = 0; i< listaNamed.length; i++)
  		{
			var name = listaNamed[i].getAttribute('name');
			var type = listaNamed[i].getAttribute('type');
			var category = listaNamed[i].getAttribute('category');
			var idNode = listaNamed[i].getAttribute('id');

			// Solo queremos elementos navegables (ways de tipo highway)
			if (( type == 'way' ) && ( category == 'highway') )
			{
				var lati = listaNamed[i].getAttribute('lat');
				var longi = listaNamed[i].getAttribute('lon');

				var el = document.createElement('h1');
				if( param == 1)
				{
					rellena1b(name, idNode);
				}
				else if( param == 2)
				{
					rellena2b(name, idNode);
				}
				break;
			}
		/*	else
			{
			//	alert('No es un way');
			}*/
		}

	}

