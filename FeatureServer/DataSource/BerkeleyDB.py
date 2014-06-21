__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: BerkeleyDB.py 451 2008-04-04 00:15:50Z brentp $"

from FeatureServer.DataSource.DBM import DBM
from FeatureServer.DataSource import DataSource
import bsddb
import _bsddb

class BerkeleyDB (DBM):
    """BerkleyDB is a specialized form of DBM, using the bsddb
       module. This is known not to work on OS X, as the bsddb
       module does not work."""
    def __init__(self, name, writable = 0, lockfile = None, **args):
        DataSource.__init__(self, name, **args)
        self.db = bsddb.rnopen( args["file"], 'c')
        self.append = self.db.db.append
        self.writable = int(writable)
        if self.writable and lockfile:
            self.lock = Lock(lockfile)
        else:
            self.lock = None

    def __iter__ (self):
        self.startIteration = True
        return self
        
    def next (self):
        if len(self.db.keys()) == 0: raise StopIteration
        if self.startIteration:
            self.startIteration = False
            return self.db.last()[0]
        try:
            return self.db.previous()[0]
        except _bsddb.DBNotFoundError:
            raise StopIteration    
