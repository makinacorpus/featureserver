__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: OSM.py 428 2008-01-19 16:16:50Z crschmidt $"

from FeatureServer.Service import Request, Action 
from FeatureServer.Feature import Feature

class OSM(Request):
    def encode(self, result):
        results = ["""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.4" generator="FeatureServer">"""]
        
        for action in result:
            for i in action:
                results.append( self.encode_feature(i))
        results.append("</osm>")
        return "application/xml", "\n".join(results)
    
    def encode_feature(self, feature):
        import xml.dom.minidom as m
        import types
        doc = m.Document()
        if feature.geometry['type'] == "Point":
            node = self.create_node(-feature.id, feature.geometry['coordinates'][0])
            for key, value in feature.properties.items():
                if isinstance(value, types.NoneType):
                    continue
                if isinstance(value, str):
                    value = unicode(attr_value, "utf-8")
                if isinstance(value, int):
                    value = str(value)
                tag = doc.createElement("tag")
                tag.setAttribute("k", key)
                tag.setAttribute("v", value)
                node.appendChild(tag)
            return node.toxml()
        elif feature.geometry['type'] == "Line" or feature.geometry['type'] == "Polygon":
            xml = ""
            i = 0
            way = doc.createElement("way")
            way.setAttribute("id", str(-feature.id))
            coords = None
            if feature.geometry['type'] == "Line":
                coords = feature.geometry['coordinates']
            else:    
                coords = feature.geometry['coordinates'][0]
            for coord in coords:
                i+=1
                xml += self.create_node("-%s000000%s" % (feature.id, i), coord).toxml()
                nd = doc.createElement("nd")
                nd.setAttribute("ref", "-%s000000%s" % (feature.id, i))
                way.appendChild(nd)
            for key, value in feature.properties.items():
                if isinstance(value, types.NoneType):
                    continue
                if isinstance(value, str):
                    value = unicode(attr_value, "utf-8")
                if isinstance(value, int):
                    value = str(value)
                tag = doc.createElement("tag")
                tag.setAttribute("k", key)
                tag.setAttribute("v", value)
                way.appendChild(tag)
            xml += way.toxml()
            return xml    
        return ""   
    def create_node(self, id, geom):
        import xml.dom.minidom as m
        doc = m.Document()
        node = doc.createElement("node")
        node.setAttribute("id", str(id)) 
        node.setAttribute("lat", "%s" % geom[1]) 
        node.setAttribute("lon", "%s" % geom[0])
        return node
