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
#    "<street name='#{name}' length='#{length}' />"
    "<name>#{name}</name>"
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
  def to_kml verbose=true
#    ret = "<edge>"
    ret = "<Placemark>"
    #If verbose=true inserts payload converted to xml
    ret << payload.to_kml if verbose
    ret << "<LineString>"
    ret << "<coordinates>"
#        -122.364383,37.824664,0 -122.364152,37.824322,0
    ret << "#{geom}"
    ret << "</coordinates>"
    ret << "</LineString>"
    ret << "</Placemark>"
#    ret << "</edge>"
  end
end

#Overrides class Graphserver to override format_shortest_path
class Graphserver

  #Formats a shortest path response depending on the format parameter
  def format_shortest_path vertices, edges, format
    ret = []
    ret << "<?xml version='1.0' encoding='UTF-8'?>"
    if format == "kml" then
      ret << "<kml xmlns='http://www.opengis.net/kml/2.2'>"
      ret << "<Document>"
      #Converts to kml the first vertex
      ret << vertices.shift.to_kml
      edges.each do |edge|
        #For each edge, converts the edge to kml
        ret << edge.to_kml
        #Shifts to the next vertex and converts to kml
        ret << vertices.shift.to_kml
      end
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

