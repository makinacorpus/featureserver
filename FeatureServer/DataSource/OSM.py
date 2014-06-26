__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: Twitter.py 412 2008-01-01 08:15:59Z crschmidt $"

from FeatureServer.DataSource import DataSource
from FeatureServer.Feature import Feature

import urllib
import xml.dom.minidom

class OSM (DataSource):
    osmxapi_url = "http://www.informationfreeway.org/api/0.5/"    
    
    """Specialized datasource allowing read-only access to OpenStreetMap"""
    def __init__(self, name, osmxapi="false", uninteresting_tags = "attribution,created_by", **args):
        DataSource.__init__(self, name, **args)
        self.uninteresting_tags = uninteresting_tags.split(",")
        self.osmxapi = osmxapi.lower() in ("true", "1", "yes") 
        
    def select (self, action):
        if self.osmxapi:
            data = self.select_osmxapi(action)
        else:
            data = self.select_main(action)
        
        doc = xml.dom.minidom.parseString(data)
        nodes = {}
        features = []
        for node in doc.getElementsByTagName("node"):
            properties = {}
            interesting = False
            for tag in node.getElementsByTagName("tag"):
                key = tag.getAttribute("k")
                properties[key] = tag.getAttribute("v")
                if not key in self.uninteresting_tags:
                    interesting = True
                    
            id = int(node.getAttribute("id"))
            nodes[id] = [float(node.getAttribute("lon")), float(node.getAttribute("lat"))]
            if interesting == True:
                geom = {'type':'Point', 'coordinates':[nodes[id]]}
                features.append(Feature(id,geom, properties))
        
        for way in doc.getElementsByTagName("way"):
            geometry = {'type':'Line', 'coordinates':[]}
            for nd in way.getElementsByTagName('nd'):
                geometry['coordinates'].append(nodes[int(nd.getAttribute("ref"))])
            properties = {}
            
            for tag in way.getElementsByTagName("tag"):
                key = tag.getAttribute("k")
                properties[key] = tag.getAttribute("v")
            
            features.append(Feature(int(way.getAttribute("id")),geometry, properties))
        
        return features
    
    def select_osmxapi(self, action):
        if action.id:
            return self.select_main(action)
        else:
            predicates = []
            for key,value in action.attributes.items():
                predicates.append("[%s=%s]" % (key, value))
            if action.bbox:
                predicates.append("[bbox=%s]" % ",".join(map(str,action.bbox)))
            
            url = "%sway%s" % (self.osmxapi_url, "".join(predicates))
            return urllib.urlopen(url).read()
            
    def select_main(self, action):
        if action.id:
            u = urllib.urlopen("http://openstreetmap.org/api/0.5/way/%s/full" % action.id)
        elif action.bbox: 
            u = urllib.urlopen("http://openstreetmap.org/api/0.5/map?bbox=%s" % ",".join(map(str, action.bbox)))
        else:
            raise Exception("Only bounding box queries or queries for way-by-ID are acceptable.")
        data = u.read()    
        if len(data) == 1:
            raise Exception("OSM Server Error: %s" % u.info().get('error'))
        return data
