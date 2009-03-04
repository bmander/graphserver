from django.http import HttpResponse
from django.shortcuts import render_to_response
from settings import GMAPS_API_KEY, DISPATCHER_HOSTNAME
from urllib import urlopen
import json

def index(request):
    children = json.loads( urlopen( "http://"+DISPATCHER_HOSTNAME+"/children" ).read() )
    childcenters = [{'name':child['name'], 'lat':(child['bounds'][1]+child['bounds'][3])/2, 'lon':(child['bounds'][0]+child['bounds'][2])/2} for child in children]
    
    return render_to_response( "index.html", {'gmaps_api_key':GMAPS_API_KEY, 'childcenters':childcenters} )
    
def contour(request):
    fp = urlopen( "http://"+DISPATCHER_HOSTNAME+request.get_full_path() )
    return HttpResponse( fp.read() )
