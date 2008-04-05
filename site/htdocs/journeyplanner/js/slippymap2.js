var map;
var markers;
var ORIGIN = 0;
var DESTINY = 1;
var marker_origin;
var marker_destiny;

function init(){
  // set map width and height
  mySize = windowSize();
  var mapWidth = mySize[0] - 300;
  var mapHeight = mySize[1];
  document.getElementById("map_frame").innerHTML= "<div id='map' style='width:"+mapWidth+"px; height:"+mapHeight+"px'></div>";

  map = new OpenLayers.Map ("map", {
			controls:[
				new OpenLayers.Control.MouseDefaults(),
				new OpenLayers.Control.LayerSwitcher(),
//				new OpenLayers.Control.MousePosition(),
				new OpenLayers.Control.PanZoomBar()],
			maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
			numZoomLevels:18, maxResolution:156543, units:'meters', projection: "EPSG:41001"} );


  var layerTah = new OpenLayers.Layer.TMS(
            "Osmarender",
            "http://tah.openstreetmap.org/Tiles/tile/",
            {type:'png', getURL: get_osm_url} );

  var layerMapnik = new OpenLayers.Layer.TMS(
            "Mapnik (actualizaci&oacute;n semanal)",
            "http://tile.openstreetmap.org/mapnik/",
            {type:'png', getURL: get_osm_url} );

  var layerKosmos = new OpenLayers.Layer.TMS(
            "Callejero",
            "http://glup.uv.es/~jjordan/tiles/",
            {type:'png', getURL: get_osm_url} );


//  var wms = new OpenLayers.Layer.WMS( "OpenLayers WMS",
//      "http://inspire.cop.gva.es/cgi-bin/mapserv?map=/etc/mapserver/inspire/wms_base.map", {layers: 'grupo_odcv05_current'} );

  map.addLayers([layerTah, layerMapnik, layerKosmos]);

  map.setCenter(lonLatToMercator(new OpenLayers.LonLat(-0.376357,39.469820)), 13);

  map.events.register("click", map, function(e) {
          var lonlat = mercatorToLonLat(map.getLonLatFromViewPortPx(e.xy));
/*          alert("You clicked near " + lonlat.lat + ", "
                                    + lonlat.lon);*/
//          addMarkerAtLonLat(lonlat.lon, lonlat.lat);
          clickando(lonlat);
      });

  markers = new OpenLayers.Layer.Markers( "Markers" );
        map.addLayer(markers);

//  addMarkerAtLonLat(-0.376357,39.469820, DESTINY);
}

function addMarkerAtLonLat (lon, lat, type) {
//function addMarkerAtLonLat (lon, lat) {
  var size = new OpenLayers.Size(24,38);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon;
  if (type == ORIGIN) {
    icon = new OpenLayers.Icon('img/icon-from.png',size,offset);
    if (marker_origin == undefined) {
      marker_origin = new OpenLayers.Marker(lonLatToMercator(new OpenLayers.LonLat(lon,lat)),icon);
      markers.addMarker(marker_origin);
      }
    else {
      markers.removeMarker(marker_origin);
      marker_origin = new OpenLayers.Marker(lonLatToMercator(new OpenLayers.LonLat(lon,lat)),icon);
      markers.addMarker(marker_origin);
    }
  }
  else {
    icon = new OpenLayers.Icon('img/icon-to.png',size,offset);
    if (marker_destiny == undefined) {
      marker_destiny = new OpenLayers.Marker(lonLatToMercator(new OpenLayers.LonLat(lon,lat)),icon);
      markers.addMarker(marker_destiny);
      }
    else {
      markers.removeMarker(marker_destiny);
      marker_destiny = new OpenLayers.Marker(lonLatToMercator(new OpenLayers.LonLat(lon,lat)),icon);
      markers.addMarker(marker_destiny);
    }
  }
}

function get_osm_url (bounds) {
  var res = this.map.getResolution();
  var x = Math.round ((bounds.left - this.maxExtent.left) / (res *
  this.tileSize.w));
  var y = Math.round ((this.maxExtent.top - bounds.top) / (res *
  this.tileSize.h));
  var z = this.map.getZoom();
  var path = z + "/" + x + "/" + y + "." + this.type;
  var url = this.url;
  if (url instanceof Array) {
    url = this.selectUrl(path, url); }
  return url + path;
}

function lonLatToMercator(ll) {
  var lon = ll.lon * 20037508.34 / 180;
  var lat = Math.log(Math.tan((90 + ll.lat) * Math.PI / 360)) / (Math.PI / 180);
  lat = lat * 20037508.34 / 180;
  return new OpenLayers.LonLat(lon, lat);
}

function mercatorToLonLat(merc) {
   var lon = (merc.lon / 20037508.34) * 180;
   var lat = (merc.lat / 20037508.34) * 180;

   lat = 180/Math.PI * (2 * Math.atan(Math.exp(lat * Math.PI / 180)) - Math.PI / 2);

   return new OpenLayers.LonLat(lon, lat);
}

// Returns the size of the browser window frame
function windowSize() {
  var mySize = new Array(2);
  var myWidth = 0, myHeight = 0;
  if( typeof( window.innerWidth ) == 'number' ) {
    //Non-IE
    myWidth = window.innerWidth;
    myHeight = window.innerHeight;
    } else if( document.documentElement &&
    ( document.documentElement.clientWidth || document.documentElement.clientHeight ) ) {
    //IE 6+ in 'standards compliant mode'
    myWidth = document.documentElement.clientWidth;
    myHeight = document.documentElement.clientHeight - 10;
    } else if( document.body && ( document.body.clientWidth || document.body.clientHeight ) ) {
    //IE 4 compatible
    myWidth = document.body.clientWidth;
    myHeight = document.body.clientHeight - 10;
    }
  mySize[0]=myWidth;
  mySize[1]=myHeight;
  return mySize;
}
