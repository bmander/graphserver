#Overrides class Calendar to add to_kml function
class Calendar
  def to_kml
#    "<calendar begin_time='#{Time.at(begin_time)}' end_time='#{Time.at(end_time)}' service_ids='#{service_ids.join(", ")}' />"
  end
end

#Overrides class Link to add to_kml function
class Link
  def to_kml
#    "<link/>"
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
#    ret = ["<triphopschedule service_id='#{service_id}'>"]
#    #Para cada triphop inserta su transformacion a xml
#    triphops.each do |triphop|
#      #Ret es un Array, << añade un elemento al final de este
#      ret << triphop.to_xml
#    end
#    ret << "</triphopschedule>"
#
#    #Convierte el Array a String
#    return ret.join
  end
end

#Overrides class TripHop to add to_kml function
class TripHop
#  SEC_IN_HOUR = 3600
#  SEC_IN_MINUTE = 60

  def to_kml
#    s_depart = "#{sprintf("%02d", depart/SEC_IN_HOUR)}:#{sprintf("%02d", (depart%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", depart%SEC_IN_MINUTE)}"
#    s_arrive = "#{sprintf("%02d", arrive/SEC_IN_HOUR)}:#{sprintf("%02d", (arrive%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", arrive%SEC_IN_MINUTE)}"
#    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' />"
#    ret = ["Trip id: #{trip_id}<br>"]
#    ret << "Departure: #{s_depart}<br>"
#    ret << "Arrival: #{s_arrive}"
#    return ret.join
    "#{trip_id}"
  end
end

#Overrides class State to add to_kml function
class State
  def to_kml
#    #Abre la cabecera del elemento state
#    ret = "<state "
#    #Insercion de atributos. Convierte la instancia de State
#    #en un hash y, para cada pareja clave-valor
#    self.to_hash.each_pair do |name, value|
#      if name == "time" then #TODO kludge alert
#        #Si la clave es "time", inserta "time='value'"
#        #formateando value como tiempo
#        ret << "time='#{Time.at( value ).inspect}' "
#      else
#        #En caso contrario escrive "name='value'"
#        #a menos que el objeto value posea un mÃ©todo to_xml
#        ret << "#{name}='#{CGI.escape(value.to_s)}' " unless value.public_methods.include? "to_xml"
#      end
#    end
#    #Cierra la cabecera del elemento state
#    ret << ">"
#
#    #Insercion de subelementos. Para cada par clave-valor
#    #que tenga un metodo to_xml, inserta el resultado de to_xml
#    self.to_hash.each_pair do |name, value|
#      ret << value.to_xml if value.public_methods.include? "to_xml"
#    end
#
#    #Cierra el elemento state, en este caso ya es un String
#    #y no necesita convertir de Array a String con join
#    ret << "</state>"
  end
end

#Overrides class Vertex to add to_kml function
class Vertex
  def to_kml
#    ret = ["<vertex label='#{label}'>"]
#    #La siguiente instruccion es una comparacion del resultado
#    #de una asignacion (= en lugar de ==)
#    #Si el objeto Vertex tiene payload lo transforma a xml
#    if pl=payload then #to avoid calling payload twice. instantiating a variable may actually be more expensive.
#      ret << pl.to_xml
#    end
#    ret << "</vertex>"
#    return ret.join
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
#    ret = ""
#    name = ""
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
#        #Compare with the last geom which is supposed to be ordered
#        #to check if the new geom is reversed
#        if (coords.last == @@coords.last) then
#          coords.reverse!
#        end
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
#      else
#        if (coords.last == @@coords.last) then
#          #Reverse and delete first point
#          coords.reverse!
#          coords.shift
#        else
#          if (coords.first == @@coords.first) then
#            #Reverse the added geometry and delete first point of the new one
#            @@coords.reverse!
#            coords.shift
#          else
#            if (coords.last == @@coords.first) then
#              #Reverse both geometrys and delete first point of the new one
#              @@coords.reverse!
#              coords.reverse!
#              coords.shift
#            end
#          end
#        end
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

  #Doesn't work! can't change geom and to from edge
#  def consolidate_path! vertices, edges
#    vertices2 = []
#    edges2 = []
#    last_name = ""
#    last_type = ""
#    vertices2 << vertices.shift
#    e = edges[0]
#    edges.each do |edge|
#      name = edge.payload.name
#      type = edge.payload.class
#      if type==last_type and name==last_name then
#        #Add coordinates
#        e.geom += " #{edge.geom}"
#        e.to = edge.to
#      else
#        edges2 << e
#        vertices2 << e.to
#        e = edge
#      end
#      last_name = name
#      last_type = type
#    end
#    vertices = vertices2
#    edges = edges2
#    puts "Edges2 length: #{edges2.length}"
#    puts "Edges length: #{edges.length}"
#  end

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
      ret << "<href>http://robotica.uv.es/~jjordan/walk.png</href>"
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
      ret << "<href>http://robotica.uv.es/~jjordan/bus.png</href>"
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
        ret << edge.to_xml
        #Shifts to the next vertex and converts to xml
        ret << vertices.shift.to_xml
      end
      ret << "</route>"
    end

  end

end

