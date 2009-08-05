import processing.opengl.*;
import org.json.*;
import java.awt.event.*;

class MouseWheelInput implements MouseWheelListener {
  SPT spt;
  
  MouseWheelInput(SPT spt) {
    this.spt = spt;
  }
  
  void mouseWheelMoved( MouseWheelEvent e ) {
    int step = e.getWheelRotation();
    maxsize *= (1.0 + step*0.1);
    ortho(-maxsize*0.5, maxsize*0.5, -maxsize*0.5, maxsize*.5, -maxsize, maxsize);
  }
}

class Box {
  public float minx;
  public float miny;
  public float minz;
  public float maxx;
  public float maxy;
  public float maxz;

  Box(float minx, float miny, float minz, float maxx, float maxy, float maxz) {
    this.minx = minx;
    this.miny = miny;
    this.minz = minz;
    this.maxx = maxx;
    this.maxy = maxy;
    this.maxz = maxz;
  }

  void draw() {
    stroke(0);
    strokeWeight(1);

    line(this.minx,this.miny,this.minz,this.maxx,this.miny,this.minz);
    line(this.maxx,this.miny,this.minz,this.maxx,this.maxy,this.minz);
    line(this.maxx,this.maxy,this.minz,this.minx,this.maxy,this.minz);
    line(this.minx,this.maxy,this.minz,this.minx,this.miny,this.minz);

    line(this.minx,this.miny,this.maxz,this.maxx,this.miny,this.maxz);
    line(this.maxx,this.miny,this.maxz,this.maxx,this.maxy,this.maxz);
    line(this.maxx,this.maxy,this.maxz,this.minx,this.maxy,this.maxz);
    line(this.minx,this.maxy,this.maxz,this.minx,this.miny,this.maxz);

    line(this.minx,this.miny,this.minz,this.minx,this.miny,this.maxz);
    line(this.maxx,this.miny,this.minz,this.maxx,this.miny,this.maxz);
    line(this.maxx,this.maxy,this.minz,this.maxx,this.maxy,this.maxz);
    line(this.minx,this.maxy,this.minz,this.minx,this.maxy,this.maxz);
  }

  float maxsize() {
    return mag(this.maxx-this.minx,this.maxy-this.miny,this.maxz-this.minz);
  }

  float x() {
    return (this.maxx-this.minx)/2+this.minx; 
  }
  float y() {
    return (this.maxy-this.miny)/2+this.miny; 
  }
  float z() {
    return (this.maxz-this.minz)/2+this.minz;
  }

}

class Point {
  float x;
  float y;
  float z;
  
  Point( float x, float y, float z ) {
    this.x = x;
    this.y = y;
    this.z = z; 
  }
}

class SPTLine {
  String linetype;
  String v1;
  String v2;
  Vector points;
  float width;

  SPTLine(String linetype, String v1, String v2) throws JSONException{
    this.linetype = linetype;
    this.width = 1;
    this.v1 = v1;
    this.v2 = v2;
    this.points = new Vector();
  }
  
  Point first() {
    return (Point)this.points.get(0); 
  }
  
  Point last() {
    return (Point)this.points.get(this.points.size()-1);
  }
  
  void add_point( Point pp ) {
    this.points.add( pp ); 
  }
  
  void draw_line( float xscale, float yscale, float zscale, float maxz ) {
    for(int i=0; i<this.points.size()-1; i++) {
      Point p1 = (Point)this.points.get( i );
      Point p2 = (Point)this.points.get( i+1 );
      line(p1.x*xscale, p1.y*yscale, p1.z*zscale, p2.x*xscale, p2.y*yscale, p2.z*zscale);
    } 
  }

  void draw(float xscale, float yscale, float zscale, float maxz) {
    if( this.last().z > maxz ){
      return; 
    }
    
    if( this.linetype.equals( "Board" ) ) {
      strokeWeight(1*this.width);
      stroke(0,255,0);
      draw_line( xscale, yscale, zscale, maxz );
    } else if (this.linetype.equals( "Distance" )) {
      strokeWeight(1*this.width);
      stroke(0,0,255);
      draw_line( xscale, yscale, zscale, maxz );
    } else if (this.linetype.equals( "Alight" )){
      strokeWeight(2*this.width);
      stroke(255,0,0);
      Point first = this.first();
      line(first.x*xscale, first.y*yscale, first.z*zscale, first.x*xscale+0.1, first.y*yscale+0.1, first.z*zscale+0.1);
    } else if (this.linetype.equals( "OSMStreet" )) {
      strokeWeight(1*this.width);
      stroke(0,0,0);
      draw_line( xscale, yscale, zscale, maxz );
    }  else if (this.linetype.equals( "StationLink" )) {
      strokeWeight(1*this.width);
      stroke(0,255,255);
      draw_line( xscale, yscale, zscale, maxz );
    } else {
      strokeWeight(1*this.width);
      stroke(0);
      draw_line( xscale, yscale, zscale, maxz );
    }
    
  }
}

class SPT {
  Box extremes;
  SPTLine[] lines;
  String[] data;
  float xscale;
  float yscale;
  float zscale;
  HashMap parent;
  
  void init(String[] data, float xscale, float yscale, float zscale) throws JSONException{
    this.xscale = xscale;
    this.yscale = yscale;
    this.zscale = zscale;
    this.data = data;
    this.parent = new HashMap();

    float minx = 10000000000.0;
    float miny = 10000000000.0;
    float minz = 10000000000.0;
    float maxx = -10000000000.0;
    float maxy = -10000000000.0;
    float maxz = -10000000000.0;

    this.lines = new SPTLine[data.length];
    for(int i=0; i<data.length; i++) {
      String[] rawline = split(data[i], ",");
      
      String v1 = rawline[1];
      String v2 = rawline[2];
      
      this.lines[i] = new SPTLine( rawline[0], v1, v2 );
      for(int j=3; j<rawline.length; j+=3) {
        float x = float(rawline[j]);
        float y = float(rawline[j+1]);
        float z = float(rawline[j+2]);
        this.lines[i].add_point( new Point(x,y,z) );
        minx = min(minx,x);
        maxx = max(maxx,x);
        miny = min(miny,y);
        maxy = max(maxy,y);
        minz = min(minz,z);
        maxz = max(maxz,z);
      }
      
      this.parent.put( v2, this.lines[i] );
    }

    this.extremes = new Box(minx*xscale, miny*yscale, minz*zscale, maxx*xscale, maxy*yscale, maxz*zscale);
    
  }

  SPT(String filename, float xscale, float yscale, float zscale) throws JSONException{
    String[] strings = loadStrings(filename);
    this.init( strings, xscale, yscale, zscale );
  }

  SPT(String filename) throws JSONException {
    String[] strings = loadStrings(filename);
    this.init( strings, 1, 1, 1 );
  }
  
  SPT(String[] data, float xscale, float yscale, float zscale) throws JSONException{
    this.init( data, xscale, yscale, zscale );
  }
  
  String closest_node(float x, float y) {
    String winner = null;
    float winnerdist = 100000000;
    
    for(int i=0; i<this.lines.length; i++){
      SPTLine curr = this.lines[i];
      //float currdist = min( dist(x, y, curr.x1, curr.y1), dist(x, y, curr.x2, curr.y2) );
      float currdist = dist(x, y, curr.first().x, curr.first().y);
      if (currdist < winnerdist) {
        winnerdist = currdist;
        winner = curr.v1; 
      }
      currdist = dist(x, y, curr.first().x, curr.first().y);
      if (currdist < winnerdist) {
        winnerdist = currdist;
        winner = curr.v2; 
      }
    }
    
    return winner;
  }
  
  SPTLine getParent( String node ) {
    return (SPTLine)this.parent.get( node );
  }
  
  void highlightPath( String topnode, int width ) {
    SPTLine curr = this.getParent( topnode );
    while( curr != null ) {
      curr.width = width;
      curr = this.getParent( curr.v1 );
    } 
  }

  void draw( float maxz ) {
    //float t0 = (this.minz/3600)*3600;
    
    stroke(0);
    for(int i=0; i<this.lines.length; i++) {
      this.lines[i].draw(this.xscale, this.yscale, this.zscale, maxz);
    }
  }
}

class SPTStackNode {
  SPT spt;
  String rootnode;
  long roottime;
  
  SPTStackNode( String rootnode, long roottime, SPT spt ) {
    this.rootnode = rootnode;
    this.roottime = roottime;
    this.spt = spt; 
  }
}

/*class SPTStack {
  SPTStackNode[] spts;  
  
  void init(JSONArray data, float xscale, float yscale, float zscale) throws JSONException {
    this.spts = new SPTStackNode[data.length()];
    
    for(int i=0; i<data.length(); i++) {
      JSONArray sptstacknode_json = data.getJSONArray(i);
      String rootnode = sptstacknode_json.getString(0);
      long roottime = sptstacknode_json.getLong(1);
      JSONArray spt_json = sptstacknode_json.getJSONArray(2);
      SPT spt = new SPT(spt_json, xscale, yscale, zscale);
      spts[i] = new SPTStackNode( rootnode, roottime, spt );
    }
  }
  
  SPTStack(String filename, float xscale, float yscale, float zscale) throws JSONException {
    String[] strings = loadStrings(filename);
    JSONArray data = new JSONArray( strings[0] );
    this.init( data, xscale, yscale, zscale );
  }
  
  SPT getSPT(int i){
    return this.spts[i].spt; 
  }
  
  void draw() {
    for(int i=0; i<this.spts.length; i++) {
      this.spts[i].spt.draw();
    }
  }
  
  SPT nextTree( long time ) {
    for(int i=0; i<this.spts.length; i++) {
      if( this.spts[i].roottime >= time ) {
        return this.spts[i].spt;
      }
    }
    
    return null;
  }
}*/

class Camera {
  //camera position in polar coordinates
  float theta;
  float phi;
  float radius;

  //when moving, position of destination
  float nexttheta;
  float nextphi;

  //camera position vector
  float cx;
  float cy;
  float cz;

  //target position vector
  float tx;
  float ty;
  float tz;
  
  //up vector
  float ux;
  float uy;
  float uz;
  
  //right vector
  float rx;
  float ry;
  float rz;

  Camera(float theta, float phi, float radius, float tx, float ty, float tz) {
    this.theta = theta;
    this.phi = phi;
    this.radius = radius;

    this.nexttheta = this.theta;
    this.nextphi = this.phi;

    this.tx = tx;
    this.ty = ty;
    this.tz = tz;
  }

  void new_angle(float theta, float phi) {
    this.nexttheta = theta;
    this.nextphi = phi;
  }

  void deltaTheta(float dtheta) {
    this.nexttheta += dtheta; 
  }

  void deltaPhi(float dphi) {
    this.nextphi += dphi; 
  }

  void update_camera_coords() {
    cx = tx+radius*sin(phi)*cos(theta);
    cy = ty+radius*sin(phi)*sin(theta);
    cz = tz+radius*cos(phi);
        
    ux = -1*sin(phi+PI/2)*cos(theta);
    uy = -1*sin(phi+PI/2)*sin(theta);
    uz = -1*cos(phi+PI/2);
    
    //find rightward vector
    //vector camera to target
    float ctx = cx - this.tx;
    float cty = cy - this.ty;
    float ctz = cz - this.tz;
    
    //cross product of camera and up is right
    rx = cty*uz - ctz*uy;
    ry = ctz*ux - ctx*uz;
    rz = ctx*uy - cty*ux;
    
    float mr = mag(rx,ry,rz);
    rx /= mr;
    ry /= mr;
    rz /= mr;
  }
  
  void moveY(float n) {
    tx += rx*n;
    ty += ry*n;
    tz += rz*n;
  }
  
  void moveX(float n) {
    tx += ux*n;
    ty += uy*n;
    tz += uz*n;
  }

  void advance_camera_towards_goal() {
    phi += (nextphi - phi)*0.1;
    theta += (nexttheta - theta)*0.1;
  }

  void update() {
    
    //println( theta );
    //println( phi );

    advance_camera_towards_goal();
    update_camera_coords();
  }

  void view() {
    camera(cx,cy,cz,tx,ty,tz,ux,uy,uz);
  }

  void draw() {
    strokeWeight(1);
    stroke(0);
    line(cx,cy,cz,tx,ty,tz);
    stroke(255,0,0);
    line(tx,ty,tz,cx, ty,tz);
    stroke(0,255,0);
    line(cx, ty,tz, cx, cy ,tz );
    stroke(0,0,255);
    line( cx, cy ,tz, cx, cy ,cz );
    
    stroke(255,255,0);
    line(cx,cy,cz,(cx+ux*10),(cy+uy*10),(cz+uz*10));
    stroke(0,255,255);
    line(cx,cy,cz,(cx+rx*10),(cy+ry*10),(cz+rz*10));
  }

}

class Origin {
  float x;
  float y;
  float z;

  Origin( float x, float y, float z) {
    this.x = x;
    this.y = y;
    this.z = z; 
  }
  
  void draw() {
    strokeWeight(1);
    stroke(255,0,0);
    line(x,y,z,x+50,y+0,z+0);
    stroke(0,255,0);
    line(x,y,z,x+0,y+50,z+0);
    stroke(0,0,255);
    line(x,y,z,x+0,y+0,z+50);
  }
}

class TimePlane {
  float l;
  float b;
  float r;
  float t;
  float time;
  
  TimePlane(float l, float b, float r, float t, float time) {
    this.l = l;
    this.b = b;
    this.r = r;
    this.t = t;
    this.time = time; 
  }
  
  void draw() {
    line(this.l, this.b, this.r, this.t);
  }
}

boolean cameraMode;
boolean rotateMode;
SPT spt;
//SPTStack spts;
Camera eye;
Origin origin;
long currtime;
float maxsize;
String topnode;
float maxz;

void setup(){
  size( 800, 800, P3D );
  smooth();

  cameraMode=true;
  rotateMode=true;
  
  topnode = null;

  try {

    spt = new SPT("ch.spt", 100, 100, 0.1);

  }
  catch(JSONException je) {
    println( je ); 
  }

  maxsize = spt.extremes.maxsize();
  ortho(-maxsize*0.5, maxsize*0.5, -maxsize*0.5, maxsize*.5, -maxsize, maxsize);
  strokeWeight( 1 );

  eye = new Camera( radians(-90), radians(180), spt.extremes.maxsize(), spt.extremes.x(), spt.extremes.y(), spt.extremes.z() );
  origin = new Origin( spt.extremes.x(), spt.extremes.y(), spt.extremes.z() );
  
  frame.addMouseWheelListener( new MouseWheelInput(spt) );
  
  maxz = spt.extremes.maxz/0.005;

}

void draw() {
  background(197, 209, 222);

  eye.update();

  if (cameraMode) {
    eye.view();
  } 
  else {
    camera(spt.extremes.x()+maxsize, spt.extremes.y()+maxsize, spt.extremes.z()+maxsize, spt.extremes.x(),spt.extremes.y(),spt.extremes.z(),0,0,-1);
    spt.extremes.draw();
    eye.draw();
  }

  //strokeWeight(1);
  //stroke(0);
  spt.draw( maxz );
  origin.draw();

  if( mousePressed ) {
    if( mouseButton == 37 ) {
      
      //eye.deltaTheta( 0.01*(mouseX-pmouseX) );
      //eye.deltaPhi( 0.01*(mouseY-pmouseY) );
      eye.nexttheta += 0.01*(mouseX-pmouseX);
      eye.theta += 0.01*(mouseX-pmouseX);
      eye.nextphi += 0.01*(mouseY-pmouseY);
      eye.phi += 0.01*(mouseY-pmouseY);
    } else {
      float res = height/maxsize;
      eye.moveY( (mouseX-pmouseX)/res );
      eye.moveX( -(mouseY-pmouseY)/res );
      
    }
  }
}

void mouseReleased() {
  if( mouseButton == 37 && eye.nexttheta == radians(-90) && eye.nextphi == radians(180) ) {
    float res = height/maxsize;
    float x_diff_from_center_screen = mouseX - float(width)/2;
    float y_diff_from_center_screen = float(height)/2 - mouseY;
    float x_coord_diff_from_center_screen = x_diff_from_center_screen/res;
    float y_coord_diff_from_cneter_screen = y_diff_from_center_screen/res;
    float clicky_x = (eye.tx + x_coord_diff_from_center_screen)/spt.xscale;
    float clicky_y = (eye.ty + y_coord_diff_from_cneter_screen)/spt.yscale;
    if( topnode != null ) {
      spt.highlightPath( topnode, 1 );
    }
    topnode = spt.closest_node(clicky_x, clicky_y);
    println( topnode );
    //spt.highlightPath( topnode, 5 );
  }
}

void keyPressed() {
  if( key == CODED ) {
    if( keyCode == DOWN || keyCode == UP ) {
      if( keyCode == DOWN ) {
        currtime -= 60;
        maxz -= 60;
      } else if ( keyCode == UP ){
        currtime += 60;
        maxz += 60;
      }
      ortho(-maxsize*0.5, maxsize*0.5, -maxsize*0.5, maxsize*.5, -maxsize, maxsize);
      //SPT nspt = spts.nextTree(currtime);
      //if(nspt != null) { spt = nspt; }
    }
  } 
  else {
    if( key == 'c' ) {
      cameraMode = !cameraMode; 
    } 
    else if ( key == 'a' ) {
      if( rotateMode ) {
        eye.deltaTheta( radians(90) );
      } else {
        eye.tx -= 1;
      }
    } 
    else if ( key == 'd' ) {
      if( rotateMode ) {
        eye.deltaTheta( -radians(90) );
      } else {
        eye.tx += 1; 
      }
    } 
    else if ( key == 's' ) {
      if( rotateMode ) {
        eye.deltaPhi( radians(90) );
      } else {
        eye.tz -= 1; 
      }
    } 
    else if ( key == 'w' ) {
      if( rotateMode ) {
        eye.deltaPhi( -radians(90) );
      } else {
        eye.tz += 1;  
      }
    } else if( key=='z' ) {
      eye.ty -= 1;
    } else if( key=='x' ) {
      eye.ty += 1;
    } else if( key == '-' ) {
      maxsize *= 1.1;
      println( maxsize );
      ortho(-maxsize*0.5, maxsize*0.5, -maxsize*0.5, maxsize*.5, -maxsize, maxsize);
    } else if( key == '=' ) {
      maxsize *= 0.9;
      println( maxsize );
      ortho(-maxsize*0.5, maxsize*0.5, -maxsize*0.5, maxsize*.5, -maxsize, maxsize);
    //} else if( key == 'r' ) {
    //  rotateMode = !rotateMode; 
    } else if( key == 't' ) {
      eye.new_angle( radians(-90), radians(180) );
    }
  }
}

