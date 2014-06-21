from FeatureServer.Service import Request, Action 
import re, xml.dom.minidom as m

import uuid

class ArcGML(Request):
    def encode(self, result):
        results = ["""
        <gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:fme="http://www.safe.com/gml/fme" 
        xsi:schemaLocation="http://www.safe.com/gml/fme fs.xsd">
        """]
        for action in result:
            for i in action:
                results.append( self.encode_feature(i))
        results.append("""</gml:FeatureCollection>""")
        return ("text/xml", "\n".join(results))        
    
    def encode_feature(self, feature):
        layername = re.sub(r'\W', '_', self.datasource)
        
        attr_fields = [] 
        for key, value in feature.properties.items():
            key = re.sub(r'\W', '_', key)
            attr_value = value
            if hasattr(attr_value,"replace"): 
                attr_value = attr_value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if isinstance(attr_value, str):
                attr_value = unicode(attr_value, "utf-8")
            attr_fields.append( "<fme:%s>%s</fme:%s>" % (key.title(), attr_value,key.title()) )
            
        
        
        xml = """
        <gml:featureMember><fme:fs gml:id="%s">
        <fme:OBJECTID>%s</fme:OBJECTID> 
        %s
        <gml:surfaceProperty>
        %s
        </gml:surfaceProperty>
        </fme:fs></gml:featureMember>""" % (str(uuid.uuid1()), feature.id, "\n".join(attr_fields), self.geometry_to_gml(feature.geometry))  
        return xml
    
    def geometry_to_gml(self, geometry):
        coords = " ".join(map(lambda x: "%s %s"% (x[0], x[1]), geometry['coordinates']))
        if geometry['type'] == "Point":
            raise Exception("Not implemented")
            return "<gml:Point><gml:coordinates>%s</gml:coordinates></gml:Point>" % coords
        elif geometry['type'] == "Line":
            raise Exception("Not implemented")
            return "<gml:LineString><gml:coordinates>%s</gml:coordinates></gml:LineString>" % coords
        elif geometry['type'] == "Polygon":
            coords = " ".join(map(lambda x: "%s %s"% (x[1], x[0]), geometry['coordinates'][0]))
            out = """
<gml:Surface srsName="EPSG:4326" srsDimension="2"> 
<gml:patches> 
<gml:PolygonPatch> 
<gml:exterior> 
<gml:LinearRing> 
<gml:posList>%s</gml:posList> 
</gml:LinearRing> 
</gml:exterior> 
</gml:PolygonPatch> 
</gml:patches> 
</gml:Surface> 
            """ % coords 
            return out
        else:
            raise Exception("Could not convert geometry of type %s." % geometry['type'])  
