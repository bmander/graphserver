#A little encapsulated databse for storing elevation profiles of OSM ways

import os
import sqlite3
import json

class ProfileDB:
    def __init__(self, dbname,overwrite=False):
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if overwrite:
            self.setup()
            
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE profiles (id TEXT, profile TEXT)" )
        c.execute( "CREATE INDEX profile_id ON profiles (id)" )
        self.conn.commit()
        c.close()
        
    def store(self, id, profile):
        c = self.conn.cursor()
        
        c.execute( "INSERT INTO profiles VALUES (?, ?)", (id, json.dumps( profile  )) )
        
        c.close()
        
    def get(self, id):
        c = self.conn.cursor()
        c.execute( "SELECT profile FROM profiles WHERE id = ?", (id,) )
        
        (profile,) = next(c)
        c.close()
        
        return [(ss/100.0, ee/100.0) for ss, ee in json.loads( profile )]
        
    def execute(self,sql,args=None):
        c = self.conn.cursor()
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

if __name__ == '__main__':
    main()
        
            