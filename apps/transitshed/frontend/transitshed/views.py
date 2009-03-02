from django.http import HttpResponse
from django.shortcuts import render_to_response
from settings import GMAPS_API_KEY, DISPATCHER_HOSTNAME
from urllib import urlopen

def index(request):
    return render_to_response( "index.html", {'gmaps_api_key':GMAPS_API_KEY} )
    
def contour(request):
    fp = urlopen( "http://"+DISPATCHER_HOSTNAME+request.get_full_path() )
    return HttpResponse( fp.read() )
