"""
822 	OpenLayers.Util.distVincenty=function(p1, p2) {
823 	    var a = 6378137, b = 6356752.3142,  f = 1/298.257223563;
824 	    var L = OpenLayers.Util.rad(p2.lon - p1.lon);
825 	    var U1 = Math.atan((1-f) * Math.tan(OpenLayers.Util.rad(p1.lat)));
826 	    var U2 = Math.atan((1-f) * Math.tan(OpenLayers.Util.rad(p2.lat)));
827 	    var sinU1 = Math.sin(U1), cosU1 = Math.cos(U1);
828 	    var sinU2 = Math.sin(U2), cosU2 = Math.cos(U2);
829 	    var lambda = L, lambdaP = 2*Math.PI;
830 	    var iterLimit = 20;
831 	    while (Math.abs(lambda-lambdaP) > 1e-12 && --iterLimit>0) {
832 	        var sinLambda = Math.sin(lambda), cosLambda = Math.cos(lambda);
833 	        var sinSigma = Math.sqrt((cosU2*sinLambda) * (cosU2*sinLambda) +
834 	        (cosU1*sinU2-sinU1*cosU2*cosLambda) * (cosU1*sinU2-sinU1*cosU2*cosLambda));
835 	        if (sinSigma==0) {
836 	            return 0;  // co-incident points
837 	        }
838 	        var cosSigma = sinU1*sinU2 + cosU1*cosU2*cosLambda;
839 	        var sigma = Math.atan2(sinSigma, cosSigma);
840 	        var alpha = Math.asin(cosU1 * cosU2 * sinLambda / sinSigma);
841 	        var cosSqAlpha = Math.cos(alpha) * Math.cos(alpha);
842 	        var cos2SigmaM = cosSigma - 2*sinU1*sinU2/cosSqAlpha;
843 	        var C = f/16*cosSqAlpha*(4+f*(4-3*cosSqAlpha));
844 	        lambdaP = lambda;
845 	        lambda = L + (1-C) * f * Math.sin(alpha) *
846 	        (sigma + C*sinSigma*(cos2SigmaM+C*cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)));
847 	    }
848 	    if (iterLimit==0) {
849 	        return NaN;  // formula failed to converge
850 	    }
851 	    var uSq = cosSqAlpha * (a*a - b*b) / (b*b);
852 	    var A = 1 + uSq/16384*(4096+uSq*(-768+uSq*(320-175*uSq)));
853 	    var B = uSq/1024 * (256+uSq*(-128+uSq*(74-47*uSq)));
854 	    var deltaSigma = B*sinSigma*(cos2SigmaM+B/4*(cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)-
855 	        B/6*cos2SigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2SigmaM*cos2SigmaM)));
856 	    var s = b*A*(sigma-deltaSigma);
857 	    var d = s.toFixed(3)/1000; // round to 1mm precision
858 	    return d;
859 	};
"""

from math import sin, cos, tan, atan, radians, pi, sqrt, atan2, asin

def vincenty(lat1,lon1, lat2, lon2):
    """returns distance in meters between any points earth"""
    
    a = 6378137
    b = 6356752.3142
    f = 1/298.257223563
    
    L = radians( lon2-lon1 )
    U1 = atan( (1-f) * tan( radians(lat1) ) )
    U2 = atan( (1-f) * tan( radians(lat2) ) )
    sinU1 = sin(U1); cosU1 = cos(U1)
    sinU2 = sin(U2); cosU2 = cos(U2)
    lmbda = L; lmbdaP = 2*pi
    
    iterLimit = 20
    
    while( iterLimit > 0 ):
        if abs(lmbda-lmbdaP) < 1E-12:
            break
        
        sinLambda = sin(lmbda); cosLambda = cos(lmbda)
        sinSigma = sqrt((cosU2*sinLambda) * (cosU2*sinLambda) + \
            (cosU1*sinU2-sinU1*cosU2*cosLambda) * (cosU1*sinU2-sinU1*cosU2*cosLambda))
        if sinSigma==0:
            return 0  # co-incident points

        cosSigma = sinU1*sinU2 + cosU1*cosU2*cosLambda
        sigma = atan2(sinSigma, cosSigma)
        alpha = asin(cosU1 * cosU2 * sinLambda / sinSigma)
        cosSqAlpha = cos(alpha) * cos(alpha)
        cos2SigmaM = cosSigma - 2*sinU1*sinU2/cosSqAlpha
        C = f/16*cosSqAlpha*(4+f*(4-3*cosSqAlpha))
        lmbdaP = lmbda;
        lmbda = L + (1-C) * f * sin(alpha) * \
            (sigma + C*sinSigma*(cos2SigmaM+C*cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)))
            
        iterLimit -= 1
            
    if iterLimit==0:
        return None  # formula failed to converge

    uSq = cosSqAlpha * (a*a - b*b) / (b*b);
    A = 1 + uSq/16384*(4096+uSq*(-768+uSq*(320-175*uSq)))
    B = uSq/1024 * (256+uSq*(-128+uSq*(74-47*uSq)))
    deltaSigma = B*sinSigma*(cos2SigmaM+B/4*(cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)-
            B/6*cos2SigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2SigmaM*cos2SigmaM)))
    s = b*A*(sigma-deltaSigma)
    
    return s
    
    
if __name__=='__main__':
    import time
    t0 = time.time()
    for i in range(10000):
        d = vincenty(47.68382,-122.376709, 47.683155,-122.376666)
    t1 = time.time()
    print( t1-t0 )
    print vincenty(47.68382,-122.376709, 47.68408,-122.375722)    