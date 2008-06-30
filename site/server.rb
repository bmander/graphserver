#!/usr/local/bin/ruby
require 'webrick'
include WEBrick

s = HTTPServer.new(
  :Port            => 80,
  :DocumentRoot    => Dir::pwd + "/htdocs"
)

trap("INT"){ s.shutdown }
s.start
