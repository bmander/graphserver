script_install_dir = $:[-2]   #location of the standard library

# Create ruby extension Makefile
Dir.chdir( "core" )
require 'extconf.rb'

# Modify ruby extension Makefile
makefile = File.read "Makefile"
makefile.gsub!( "edgeweights.o", "" )
makefile.gsub!( "edgeweights.c", "" )
makefile.gsub!( "router.o", "" )
makefile.gsub!( "router.c", "" )
makefile << "\nme_a_sandwich:\n\techo okay\n"

# Write modified ruby extension Makefile
fp = File.new( "Makefile", "w" )
fp << makefile
fp.close

# Execute modified ruby extension Makefile, and install resulting files
print `make clean`
print `make install`
print "installing to: #{script_install_dir}\n"
print `cp graphserver.rb #{script_install_dir}`
print `cp graph.rb #{script_install_dir}`
