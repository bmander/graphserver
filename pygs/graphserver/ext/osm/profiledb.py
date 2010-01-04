#A little encapsulated databse for storing elevation profiles of OSM ways

import os
import sqlite3
try:
    import json
except ImportError:
    import simplejson as json
import binascii
from struct import pack, unpack
    
def pack_coords(coords):
    return binascii.b2a_base64( "".join([pack( "ff", *coord ) for coord in coords]) )
        
def unpack_coords(str):
    bin = binascii.a2b_base64( str )
    return [unpack( "ff", bin[i:i+8] ) for i in range(0, len(bin), 8)]

class ProfileDB:
    def __init__(self, dbname,overwrite=False):
        self.dbname = dbname
        
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if overwrite:
            self.setup()
            
    def get_cursor(self):
        # Attempts to get a cursor using the current connection to the db. If we've found ourselves in a different thread
        # than that which the connection was made in, re-make the connection.
        
        try:
            ret = self.conn.cursor()
        except sqlite3.ProgrammingError:
            self.conn = sqlite3.connect(self.dbname)
            ret = self.conn.cursor()
            
        return ret
            
    def setup(self):
        c = self.get_cursor()
        c.execute( "CREATE TABLE profiles (id TEXT, profile TEXT)" )
        c.execute( "CREATE INDEX profile_id ON profiles (id)" )
        self.conn.commit()
        c.close()
        
    def store(self, id, profile):
        c = self.get_cursor()
        
        c.execute( "INSERT INTO profiles VALUES (?, ?)", (id, pack_coords( profile )) )
        
        c.close()
        
    def get(self, id):
        c = self.get_cursor()
        c.execute( "SELECT profile FROM profiles WHERE id = ?", (id,) )
        
        try:
            (profile,) = c.next()
        except StopIteration:
            return None
        finally:
            c.close()
        
        return unpack_coords( profile )
        
    def execute(self,sql,args=None):
        c = self.get_cursor()
        if args:
            for row in c.execute(sql,args):
                yield row
        else:
            for row in c.execute(sql):
                yield row
        c.close()

from sys import argv
def main():
    if len(argv) > 1:
        pdb = ProfileDB( argv[1] )
        
        if len(argv) > 2:
            print pdb.get( argv[2] )
        else:
            for (id,) in list( pdb.execute( "SELECT id from profiles" ) ):
                print id
    else:
        print "python profiledb.py profiledb_filename [profile_id]"

if __name__ == '__main__':
    main()
        
            
