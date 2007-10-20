def build_makefile build_dir

  #Change directories because we can't get extconf always writes Makefiles to the working directory
  pwd = Dir.pwd
  Dir.chdir( build_dir )

  # Create ruby extension Makefile
  require "extconf.rb"

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
  
  Dir.chdir( pwd )
  
end

def make build_dir
  print `make -C #{build_dir}`
end

def clean build_dir
  print `make -C #{build_dir} `
end
  
def install build_dir, script_install_dir

  # Execute modified ruby extension Makefile, and install resulting files
  print `make -c #{build_dir} install`
  print "installing to: #{script_install_dir}\n"
  print `cp #{build_dir}/graphserver.rb #{script_install_dir}`
  print `cp #{build_dir}/graph.rb #{script_install_dir}`

end

install_dir = $:[0]   #location of the standard library
build_dir = "core"

usage = "usage: ruby install.rb build|install|clean\n"

if ARGV[0] == 'build':
  build_makefile( build_dir )
  make( build_dir )
elsif ARGV[0] == 'install'
  build_makefile( build_dir )
  install( build_dir, install_dir )
elsif ARGV[0] == 'clean'
  clean( build_dir )
else
  print usage 
end