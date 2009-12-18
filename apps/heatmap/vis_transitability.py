import json
from math import floor

surface = json.loads( open("nseattle.surface").read() )

maxt = max([max([t for x,y,t in row]) for row in surface])

#north seattle
#bottom,left=(47.62722312591712-0.004, -122.35164642333984-0.004)
#top,right=(47.67902719206281+0.004, -122.28813171386719+0.004)

bottom,left=(47.66567637286265, -122.33173370361328)
top,right=(47.687405831555616, -122.30289459228516)

#red to yellow (255,0,0) to (255,255,0)
rty = zip([255]*256, range(256),[0]*256)
#yellow to green (255,255,0) to (0,255,0)
ytg = zip(range(255,-1,-1), [255]*256, [0]*256)
#green to cyan (0,255,0) to (0,255,255)
gtc = zip([0]*256, [255]*256, range(256))
#cyan to blue (0,255,255) to (0,0,255)
ctb = zip([0]*256, range(255,-1,-1), [255]*256)
#blue to violet (0,0,255) to (255,0,255)
btv = zip(range(256), [0]*256, [255]*256)

colors = rty+ytg+gtc+ctb#+btv
        
from prender import processing
mr = processing.MapRenderer()
mr.start(left,bottom,right,top,1000) #left,bottom,right,top,width
mr.background(255,255,255)
mr.smooth()
mr.stroke(255,255,255)
mr.strokeWeight(0)
mr.fill(0,0,255,128)
for col in surface:
    for lon,lat,width in col:
        if width is None:
            continue
        
        r,g,b = colors[int(width/float(maxt)*(len(colors)-1))]
        mr.fill(r,g,b)
        
        #mr.ellipse(lon,lat,0.000001*width,0.000001*width)
        mr.ellipse(lon,lat,0.0009,0.0009)
mr.saveLocal("map.png")
mr.stop()