__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: KML.py 412 2008-01-01 08:15:59Z crschmidt $"

from FeatureServer.Service import Request
from FeatureServer.Service import Action 
from FeatureServer.Feature import Feature

import re

class KML(Request):
    def encode(self, result):
        url = "%s/%s/%s-data.kml" % (self.host, self.datasource, self.datasource)
        results = ["""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.0" xmlns:fs="http://featureserver.com/ns" xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
<atom:link rel="self" href="%s" type="application/vnd.google-earth.kml+xml" /> 
<Style id="allstyle">
    <LineStyle>
        <width>5</width>
        <color>ff0099ee</color>
    </LineStyle>
    <PolyStyle>
        <color>900099ee</color>
    </PolyStyle>
</Style>
        """ % url]
        for action in result:
            for i in action:
                results.append( self.encode_feature(i))
        results.append("""</Document>
        </kml>""")
        return ("application/vnd.google-earth.kml+xml", "\n".join(results))        
    
    def encode_feature(self, feature):
        "Take a feature, and return an XML string for that feature."
        ds = self.service.datasources[self.datasource]
        name = ""
        if hasattr(ds, 'title_property') and feature.properties.has_key(ds.title_property):
            name = feature.properties[ds.title_property]        
        elif "title" in feature.properties:
            name = feature.properties['title']
        description = ""
        if feature.properties.has_key("description"):
            description = "<![CDATA[%s]]>" % feature.properties['description']
        else:    
            desc_fields = ['Properties:'] 
            for key, value in feature.properties.items():
                if key in ["styleUrl", "title"]: continue 
                if isinstance(value, str):
                        value = unicode(value, "utf-8")
                desc_fields.append( "<b>%s</b>: %s" % (key, value) )
            description = "<![CDATA[%s]]>" % ("<br />".join(desc_fields))   
        
        styleUrl = "#allstyle"
        if feature.properties.has_key("styleUrl"):
            styleUrl = feature.properties['styleUrl']
        
        attr_fields = []
        for key, value in feature.properties.items():
            key = re.sub(r'\W', '_', key)
            if key in ["title", "description", "styleUrl"]: continue
            attr_value = value
            if isinstance(attr_value, str):
                attr_value = unicode(attr_value, "utf-8")
            if hasattr(attr_value,"replace"): 
                attr_value = attr_value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            attr_fields.append( "<fs:%s>%s</fs:%s>" % (key, attr_value, key) )
        
        edit_url = "%s/%s/%s.kml" % (self.host, self.datasource, feature.id)  
        
        xml = """
        <Placemark id="%s">
        <name>%s</name>
        <description>%s</description>
        <styleUrl>%s</styleUrl>
        <atom:link href="%s" type="edit" />
        <Metadata>
          %s
        </Metadata>
        %s
        </Placemark>""" % (feature.id, name, description, styleUrl, edit_url, "\n".join(attr_fields), self.geometry_to_place(feature.geometry)) 
        return xml
    
    def geometry_to_place(self, geometry):
        coords = " ".join(map(lambda x: ",".join(map(str, x)), geometry['coordinates']))
        if geometry['type'] == "Point":
            return "<Point><coordinates>%s</coordinates></Point>" % coords
        elif geometry['type'] == "Line":
            return "<LineString><coordinates>%s</coordinates></LineString>" % coords
        elif geometry['type'] == "Polygon":
            coords = " ".join(map(lambda x: ",".join(map(str, x)), geometry['coordinates'][0]))
            out = """
              <outerBoundaryIs><LinearRing>
              <coordinates>%s</coordinates>
              </LinearRing></outerBoundaryIs>
            """ % coords 
            inner_rings = []
            for inner_ring in geometry['coordinates'][1:]:
                coords = " ".join(map(lambda x: ",".join(map(str, x)), inner_ring))
                inner_rings.append("""
                  <innerBoundaryIs><LinearRing>
                  <coordinates>%s</coordinates>
                  </LinearRing></innerBoundaryIs>
                """ % coords) 
            return """<Polygon>
              %s %s
              </Polygon>""" % (out, "\n".join(inner_rings))
        else:
            raise Exception("Could not convert geometry of type %s." % geometry['type'])  
    
    def handle_post(self, params, path_info, host, post_data, request_method):
            import xml.dom.minidom as m
            actions = []
            
            id = self.get_id_from_path_info(path_info)
            if id:
                action = Action()
                action.method = "update"
                action.id = id 
                
                doc = m.parseString(post_data)
                entry = doc.getElementsByTagName("Placemark")[0]
                feature = self.entry_to_feature(entry)
                action.feature = feature
                actions.append(action)
            
            else:
                doc = m.parseString(post_data)
                entries = doc.getElementsByTagName("Placemark")
                entries.reverse()
                for entry in entries:
                    action = Action()
                    action.method = "create"
                    feature_obj = self.entry_to_feature(entry)
                    action.feature = feature_obj
                    actions.append(action)
                
            return actions

    def entry_to_feature(self, placemark_dom):
        feature = Feature()
        points = placemark_dom.getElementsByTagName("Point")
        lines = placemark_dom.getElementsByTagName("LineString")
        polys = placemark_dom.getElementsByTagName("Polygon")
        if len(points):
            coords = points[0].getElementsByTagName("coordinates")[0].firstChild.nodeValue.strip().split(",")
            feature.geometry = {'type':'Point', 'coordinates':[map(float,coords)]}
        elif len(lines):
            coordstring = lines[0].getElementsByTagName("coordinates")[0].firstChild.nodeValue.strip()
            coords = coordstring.split(" ")
            coords = map(lambda x: x.split(","), coords)
            feature.geometry = {'type':'Line', 'coordinates':coords}
        elif len(polys):
            rings = []
            poly = polys[0]
            outer = poly.getElementsByTagName("outerBoundaryIs")[0]
            outer_coordstring = outer.getElementsByTagName("coordinates")[0].firstChild.nodeValue.strip()
            outer_coords = outer_coordstring.split(" ")
            outer_coords = map(lambda x: x.split(","), outer_coords)
            rings.append(outer_coords)
            inners = poly.getElementsByTagName("innerBoundaryIs")
            for inner in inners:
                inner_coords = inner.getElementsByTagName("coordinates")[0].firstChild.nodeValue.strip().split(" ")
                inner_coords = map(lambda x: x.split(","), inner_coords)
                rings.append(inner_coords)
                
            
            feature.geometry = {'type':'Polygon', 'coordinates':rings}
            
        else:
            raise Exception("KML parser only understands points and lines, and polys. You seem to be missing something.") 
        nodeList = placemark_dom.childNodes
        if len(placemark_dom.getElementsByTagName("Metadata")):
            nodeList += placemark_dom.getElementsByTagName("Metadata")[0].childNodes
        for node in nodeList:
            try:
                attr_name = node.tagName.split(":")[-1]
                value = node.firstChild.nodeValue
                if node.tagName not in ['Point', 'LineString', 'Polygon', 'name', 'Metadata'] and not value.startswith("Properties:"):
                    feature.properties[attr_name] = value
            except:
                pass
            
            try:
                feature.properties['title'] = placemark_dom.getElementsByTagName("name")[0].firstChild.nodeValue
            except:
                pass
        
        return feature    
