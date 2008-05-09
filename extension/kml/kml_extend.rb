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
  #A class variable to take into account if an xml tag is open
  @@open = false
  #A class variable to join coords from several stretches
  @@geom = ""
  #A class variable to store the added stretch init time
  @@init_time = ""
  #A class variable to store the added stretch end time
  @@end_time = ""
  #A class variable to store the step number
  @@step = 0

  #A class method to reset class variables
  def self.reset
    @@last_name = ""
    @@open = false
    @@geom = ""
    @@init_time = ""
    @@end_time = ""
    @@step = 0
  end

  #A class method to check wether the placemark tag is closed and close it
  def self.check_close
    if @@open then
      @@open = false
      #Print the coordinates
      ret = "#{@@geom.join(' ')}"
      ret << "</coordinates>"
      ret << "</LineString>"
      ret << "</Placemark>"
    end
  end

  #Method to open the placemark tag
  def open_placemark
    @@open = true
    @@step += 1
#    @@init_time = "#{Time.at( self.from.payload["time"] ).inspect}"
    @@init_time = Time.at( self.from.payload["time"] )

    #If verbose=true inserts payload converted to kml
    ret = "<Placemark>"
    ret << "<name>"
    ret << payload.to_kml
    ret << "</name>"
    ret << "<LineString>"
    ret << "<coordinates>"
  end

  #Method to close the placemark tag
  def close_placemark
    @@open = false
    @@end_time = Time.at( self.to.payload["time"] )
    type = payload.class

    #Print the coordinates
    ret = "#{@@geom.join(' ')}"
    ret << "</coordinates>"
    ret << "</LineString>"
    ret << "</Placemark>"

    #An icon showing the start point and description
    ret << "<Placemark>"
    ret << "<name>#{@@step.to_s.rjust(2,'0')}</name>"
    ret << "<description>"
    #Different rendering for Streets and Triphops
    if type == Street then
      ret << "#{@@init_time.strftime("%H:%M")}. "
    else
      ret << "Departure: #{@@init_time.strftime("%H:%M")}. "
      ret << "Arrival: #{@@init_time.strftime("%H:%M")}. "
    end
    ret << payload.to_kml
    ret << "</description>"
    ret << "<Point>"
    ret << "<coordinates>"
    ret << "#{@@geom[0]}"
    ret << "</coordinates>"
    ret << "</Point>"
    ret << "</Placemark>"
  end

#  def to_kml verbose=true
#    ret = "<Placemark>"
#    #If verbose=true inserts payload converted to kml
#    ret << payload.to_kml if verbose
#    ret << "<LineString>"
#    ret << "<coordinates>"
#    ret << "#{geom}"
#    ret << "</coordinates>"
#    ret << "</LineString>"
#    ret << "</Placemark>"
#  end

  def to_kml verbose=true
    ret = ""
    name = ""
    type = payload.class
    if type == Street then name = payload.name else name = payload.trip_id end
    if name != @@last_name then
      #If the stretch belongs to a diferent street, close last tag if necessary and open a new one
      @@last_name = name
      if @@open then ret << close_placemark end
      @@geom = geom.split(' ')
      ret << open_placemark
    else
      #If the stretch belongs to the same street, just add the coordinates that don't repeat the last vertex
      coords = geom.split(' ')
      #Compare first and last coordinates of coords with the last one of the added geom
      if (coords.first == @@geom.last) then
        #Delete first point
        coords.shift
      else
        if (coords.last == @@geom.last) then
          #Reverse and delete first point
          coords.reverse!
          coords.shift
        else
          if (coords.first == @@geom.first) then
            #Reverse the added geometry and delete first point of the new one
            @@geom.reverse!
            coords.shift
          else
            if (coords.last == @@geom.first) then
              #Reverse both geometrys and delete first point of the new one
              @@geom.reverse!
              coords.reverse!
              coords.shift
            end
          end
        end
      end
      #Append the coordinates of the last stretch to the added geom
      @@geom.concat(coords)
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
      #Converts to kml the first vertex
      edges.each do |edge|
        #For each edge, converts the edge to kml
        ret << edge.to_kml
      end
      #Closes the last tag
      ret << Edge.check_close
#      ret << "</coordinates>"
#      ret << "</LineString>"
#      ret << "</Placemark>"
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

