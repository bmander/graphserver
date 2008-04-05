#!/usr/local/bin/ruby
require 'webrick'
#include WEBrick

class JourneyPlanner

  #Funcion llamada al hacer JourneyPlanner.new
  def initialize
    @server = WEBrick::HTTPServer.new(
      :Port            => 80,
      :DocumentRoot    => Dir::pwd + "/htdocs/journeyplanner"
    )

    #Genera la respuesta a la peticion GET "/compute"
    @server.mount_proc( "/compute" ) do |request, response|
      from = request.query['from']
      to = request.query['to']
      ret = ["Quiero ir desde"]
      ret << "#{from}"
      ret << "hasta"
      ret << "#{to}."
      #Transforma el Array en un String de varias lineas de texto
      response.body = ret.join("\n")
    end

    #Genera la respuesta a la peticion GET "/compute2"
    @server.mount_proc( "/compute2" ) do |request, response|
      from = request.query['from']
      to = request.query['to']
      ret = ["Quiero ir desde"]
      ret << "#{from}"
      ret << "hasta"
      ret << "#{to}."
      #Transforma el Array en un String de varias lineas de texto
      response.body = ret.join("\n")
    end

  end

  #Inicia JourneyPlanner. Si el usuario teclea "CONTROL+C" el server tiene que cerrarse
  def start
    trap("INT"){ @server.shutdown }
    @server.start
  end

end

jp = JourneyPlanner.new
jp.start
