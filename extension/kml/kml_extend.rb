#Overrides class Calendar to add to_kml function
class Calendar
  def to_kml
  end
end

#Overrides class Link to add to_kml function
class Link
  def to_kml
  end
end

#Overrides class Street to add to_kml function
class Street
  def to_kml
    "#{CGI.escapeHTML(name)}"
  end
end

#Overrides class TripHopSchedule to add to_kml function
class TripHopSchedule
  def to_kml
  end
end

#Overrides class TripHop to add to_kml function
class TripHop

  def to_kml
    "#{trip_id}"
  end
end

#Overrides class State to add to_kml function
class State
  def to_kml
  end
end

#Overrides class Vertex to add to_kml function
class Vertex
  def to_kml
  end
end

#Overrides class Edge to add to_kml function
class Edge
  #A class variable to store the last edge name
  @@last_name = ""
  #A class variable to store the last edge class
  @@last_type = ""
  #A class variable to take into account if the edge is the first of the route
  @@first = true
  #A class variable to join coordinates from adjacent stretches
  @@coords = ""
  #A class variable to store the added stretch init time
  @@init_time = ""
  #A class variable to store the added stretch end time
  @@end_time = ""
  #A class variable to store the step number
  @@step = 0

  #A class method to reset class variables
  def self.reset
    @@last_name = ""
    @@last_type = ""
    @@first = true
    @@coords = ""
    @@init_time = ""
    @@end_time = ""
    @@step = 0
  end

  #Method to print the placemark tag
  def print_placemark
    #Links are not processed
#    if @@last_type == Link then return end
    #An icon showing the start point and description
    ret = "<Placemark>"
    ret << "<name>#{@@step.to_s.rjust(2,'0')}</name>"
    ret << "<description>"
    #Different rendering for Streets and Triphops
    if (@@last_type == Street || @@last_type == Link) then
      ret << "#{@@init_time.strftime("%H:%M")}. "
    else
      ret << "Departure: #{@@init_time.strftime("%H:%M")}. "
      ret << "Arrival: #{@@end_time.strftime("%H:%M")}. "
    end
#    ret << payload.to_kml
    ret << @@last_name
    ret << "</description>"
    if (@@last_type == Street || @@last_type == Link) then
      ret << "<styleUrl>#walkIcon</styleUrl>"
    else
      ret << "<styleUrl>#busIcon</styleUrl>"
    end
    ret << "<Point>"
    ret << "<coordinates>"
    ret << "#{@@coords[0]}"
    ret << "</coordinates>"
    ret << "</Point>"
    ret << "</Placemark>"

    #A polyline showing the path
    ret << "<Placemark>"
    ret << "<name>"
#    ret << payload.to_kml
    ret << @@last_name
    ret << "</name>"
    if (@@last_type == Street || @@last_type == Link) then
      ret << "<styleUrl>#walkPath</styleUrl>"
    else
      ret << "<styleUrl>#busPath</styleUrl>"
    end
    ret << "<LineString>"
    ret << "<coordinates>"
    ret << "#{@@coords.join(' ')}"
    ret << "</coordinates>"
    ret << "</LineString>"
    ret << "</Placemark>"
  end

  #Render the edge in kml format
  def to_kml verbose=true
    type = payload.class
    if type == Street then
      name = payload.name
    else
      if type == TripHop then
        name = payload.trip_id
      else
        name = ""
      end
    end
    #If the stretch belongs to a diferent street/triphop
    if name != @@last_name or type != @@last_type then
      coords = geom.split(' ')
      if not @@first then
        @@end_time = Time.at( self.to.payload["time"] )
        ret = print_placemark
      else
        @@first = false
      end
      @@step += 1
      @@init_time = Time.at( self.from.payload["time"] )
      @@last_name = name
      @@last_type = type
      @@coords = coords
      return ret
    else
      #If the stretch belongs to the same street, add all the coordinates except the first,
      #which was present in the last stretch
      coords = geom.split(' ')
      #Compare first and last coordinates of coords with the last one of the added geom
      if (coords.first == @@coords.last) then
        #Delete first point
        coords.shift
      end
      #Append the coordinates of the last stretch to the added geom
      @@coords.concat(coords)
      #Don't print anything
      return
    end
  end
end

#Overrides class Graphserver to override format_shortest_path
class Graphserver

  #Formats a shortest path response depending on the format parameter
  def format_shortest_path vertices, edges, format
    ret = []
    ret << "<?xml version='1.0' encoding='UTF-8'?>"
    if format == "kml" then
      #Reset class variables for Edge
      Edge.reset
      ret << "<kml xmlns='http://earth.google.com/kml/2.2' xmlns:atom='http://www.w3.org/2005/Atom'>"
      ret << "<Document>"
      ret << "<name>Shortest path</name>"
      #Add styles
      ret << "<Style id='walkPath'>"
      ret << "<LineStyle>"
      ret << "<color>7fff0000</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='walkIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/walk.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='tramPath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='tramIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/tram.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='subwayPath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='subwayIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/subway.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='railPath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='railIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/rail.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='busPath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='busIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/bus.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='ferryPath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='ferryIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/ferry.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      ret << "<Style id='planePath'>"
      ret << "<LineStyle>"
      ret << "<color>7f0000ff</color>"
      ret << "<width>5</width>"
      ret << "</LineStyle>"
      ret << "</Style>"
      ret << "<Style id='planeIcon'>"
      ret << "<IconStyle>"
      ret << "<Icon>"
      ret << "<href>img/plane.png</href>"
      ret << "</Icon>"
      ret << "<hotSpot x='0' y='0' xunits='fraction' yunits='fraction'/>"
      ret << "</IconStyle>"
      ret << "</Style>"
      #For each edge, converts the edge to kml
      edges.each do |edge|
        ret << edge.to_kml
      end
      #Prints the last Placemark
      ret << edges.last.print_placemark
      ret << "</Document>"
      ret << "</kml>"
    else
      ret << "<route>"
      #Converts to xml the first vertex
      ret << vertices.shift.to_xml
      edges.each do |edge|
        #For each edge, converts the edge to xml
        ret << edge.to_xml(@conn)
        #Shifts to the next vertex and converts to xml
        ret << vertices.shift.to_xml(@conn)
      end
      ret << "</route>"
    end

  end

end

