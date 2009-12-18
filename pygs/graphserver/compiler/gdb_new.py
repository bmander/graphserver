from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
import os

def main():
    usage = """usage: python new_gdb.py [options] <graphdb_filename> """
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--overwrite",
                      action="store_true", dest="overwrite", default=False,
                      help="overwrite any existing database")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.print_help()
        exit(-1)
    
    graphdb_filename = args[0]
    
    if not os.path.exists(graphdb_filename) or options.overwrite:
        print "Creating graph database '%s'"%graphdb_filename
        
        graphdb = GraphDatabase( graphdb_filename, overwrite=options.overwrite )
    else:
        print "Graph database '%s' already exists. Use -o to overwrite"%graphdb_filename

if __name__=='__main__':
    main()