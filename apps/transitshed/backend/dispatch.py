from servable import Servable
import json
from rtree import Rtree
from urllib import urlencode
from urllib import urlopen
import yaml

class Dispatch:
    def __init__(self, config_filename):
        self.index = Rtree()
        
        # get children from yaml file
        config_str = open(config_filename).read()
        print config_str
        self.children = yaml.load( config_str )
        
        # index children according to their bounding box
        for i, child in enumerate(self.children):
            self.index.add(i, child['bounds'])
    
    def register(self, baseurl, left, bottom, right, top):
        if baseurl in self.children.values():
            raise Exception( "Child with baseurl '%s' already registered"%baseurl )
        
        childindex = len(self.children)
        self.children[childindex] = (baseurl, (left,bottom,right,top))
        self.index.add( childindex, (left, bottom, right, top) )
        
        return json.dumps(self.children)
        
    def children(self):
        return json.dumps(self.children.values())
        
    def _over(self, lat, lon):
        return [self.children[x] for x in self.index.intersection( (lon, lat, lon, lat) )]
            
    def contour(self, lat, lon, year, month, day, hour, minute, second, cutoff, step=60*15, encoded=False, speed=0.85):
        child_servers = self._over( lat, lon )
        if len(child_servers) == 0:
            return "NO SHEDS HERE"
        
        child_server = child_servers[0]
        args = {'lat':lat,
                'lon':lon,
                'year':year,
                'month':month,
                'day':day,
                'hour':hour,
                'minute':minute,
                'second':second,
                'cutoff':cutoff,
                'step':step,
                'speed':speed}
        contoururl = "http://%s/contour?%s&encoded=true"%(child_server['url'], urlencode(args))
        return urlopen(contoururl).read()
            
class DispatchServer(Servable,Dispatch):
    def over(self, lat, lon):
        return json.dumps( Balancer._over(self, lat, lon) )
        
        
if __name__=='__main__':
    ds = DispatchServer("children.yaml")
    ds.run_test_server(8080)
    