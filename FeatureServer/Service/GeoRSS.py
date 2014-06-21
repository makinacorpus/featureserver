__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: GeoRSS.py 412 2008-01-01 08:15:59Z crschmidt $"

from FeatureServer.Service import Request
from FeatureServer.Service import Action
from FeatureServer.Service import NoLayerException 
from FeatureServer.Feature import Feature
import time
import sys
from datetime import datetime

class GeoRSS(Request):
    def parse(self, params, path_info, host, post_data, request_method):
        try:
            self.get_layer(path_info, params) 
        except NoLayerException:
            action = Action()
            action.method = "metadata"
            self.host = host
            self.actions.append(action)
            return 
        
        Request.parse(self, params, path_info, host, post_data, request_method) 
            
    def encode_metadata(self, action):
        layers = self.service.datasources
        layer_text = []
        for layer in layers.keys():
            layer_text.append("<collection href='%s/%s/all.atom'><atom:title>%s</atom:title></collection>" % (self.host, layer, layer))
            
        action.metadata = """<?xml version="1.0" encoding="utf-8"?>
<service xmlns="http://www.w3.org/2007/app" xmlns:atom="http://www.w3.org/2005/Atom">
  <workspace>
    <atom:title>FeatureServer</atom:title>
    %s
  </workspace>
</service>
""" % ("\n".join(layer_text))
        return ("application/rss+xml", action.metadata)
    
    def encode(self, result):
        timestamp = datetime.fromtimestamp(time.time())
        timestamp = str(timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'))
        url = "%s/%s?format=atom" % (self.host, self.datasource)
        results = ["""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app" 
              xmlns:georss="http://www.georss.org/georss">
              <title>%s</title>
              <id>%s</id>
              <link rel="self" href="%s" />
              <author><name>FeatureServer</name></author>
              <updated>%s</updated>
              """ % (self.datasource, url, url, timestamp) ]
        
        for action in result:
            for i in action:
                results.append( self.encode_feature(i))
        
        results.append("</feed>")  
        return ("application/atom+xml", "\n".join(results))
    
    def encode_feature(self, feature):
        import xml.dom.minidom as m
        doc = m.Document()
        entry = doc.createElement("entry")
        
        id_node = doc.createElement("id")
        id_node.appendChild(doc.createTextNode("%s/%s/%s.atom" % (self.host, self.datasource, feature.id)))
        entry.appendChild(id_node)
        
        link_node = doc.createElement("link")
        link_node.setAttribute("href", "%s/%s/%s.atom" % (self.host, self.datasource, feature.id))
        entry.appendChild(link_node)
        
        link_node = doc.createElement("link")
        link_node.setAttribute("href", "%s/%s/%s.atom" % (self.host, self.datasource, feature.id))
        link_node.setAttribute("rel", "edit")
        entry.appendChild(link_node)
        
        title_node = doc.createElement("title")
        title = None
        if feature.properties.has_key("title"):
            title = doc.createTextNode(feature.properties['title'])
        else:    
            title = doc.createTextNode("Feature #%s" % feature.id)
        title_node.appendChild(title)
        entry.appendChild(title_node)
        
        if feature.properties.has_key('timestamp'):
            timestamp = feature.properties['timestamp']
            del feature.properties['timestamp']
            edited = doc.createElement("app:edited")
            item_time = datetime.fromtimestamp(timestamp)
            edited.appendChild(doc.createTextNode(str(item_time.strftime('%Y-%m-%dT%H:%M:%SZ'))))
            entry.appendChild(edited)
            updated = doc.createElement("updated")
            timestamp = datetime.fromtimestamp(timestamp)
            updated.appendChild(doc.createTextNode(str(timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'))))
            entry.appendChild(updated)
        else:
            updated = doc.createElement("updated")
            timestamp = datetime.fromtimestamp(time.time())
            updated.appendChild(doc.createTextNode(str(timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'))))
            entry.appendChild(updated)
            
        desc_node = doc.createElement("content")
        desc_node.setAttribute("type", "html")
        description = ""
            
        if feature.properties.has_key("description"):
            description = feature.properties['description']
        else:
            desc_fields = []
            for key, value in feature.properties.items():
                if isinstance(value, str):
                    value = unicode(value, "utf-8")
                desc_fields.append( "<b>%s</b>: %s" % (key, value) )
            description = "%s" % ("<br />".join(desc_fields)) 
        desc_node.appendChild(doc.createTextNode(description))
        entry.appendChild(desc_node)
        
        coords = " ".join(map(lambda x: "%s %s" % (x[1], x[0]), feature.geometry['coordinates']))
        if feature.geometry['type'] == "Point" or feature.geometry['type'] == "Line":
            geo_node = doc.createElement("georss:%s" % (feature.geometry['type'].lower()))
            geo_node.appendChild(doc.createTextNode(coords))
        
        else:
            coords = " ".join(map(lambda x: "%s %s" % (x[1], x[0]), feature.geometry['coordinates'][0]))
            geo_node = doc.createElement("georss:polygon")
            geo_node.appendChild(doc.createTextNode(coords))
            
        entry.appendChild(geo_node)
        
        return entry.toxml()
    
    def handle_post(self, params, path_info, host, post_data, request_method):
            import xml.dom.minidom as m
            actions = []
            
            id = self.get_id_from_path_info(path_info)
            if id:
                action = Action()
                action.method = "update"
                action.id = id 
                
                doc = m.parseString(post_data)
                entries = doc.getElementsByTagName("entry")
                if not entries:
                    entries = doc.getElementsByTagName("item")
                entry = entries[0]
                feature = self.entry_to_feature(entry)
                action.feature = feature
                if feature:
                    actions.append(action)
            
            else:
                try:
                    doc = m.parseString(post_data)
                except Exception, E:
                    raise Exception("Unable to parse GeoRSS. (%s)\nContent was: %s" % (E, post_data))
                entries = doc.getElementsByTagName("entry")
                if not entries:
                    entries = doc.getElementsByTagName("item")
                entries.reverse()
                for entry in entries:
                    action = Action()
                    action.method = "create"
                    feature_obj = self.entry_to_feature(entry)
                    action.feature = feature_obj
                    if feature_obj:
                        actions.append(action)
                
            return actions
    
    def coordinates_to_geom(self, coordinates, type):
        """Convert a coordinates string from GML or GeoRSS Simple to 
           a FeatureServer internal geometry."""
        coords = coordinates.strip().replace(",", " ").split()
        if type == "Line":
            coords = [[float(coords[i+1]), float(coords[i])] for i in xrange(0, len(coords), 2)]
            return {'type':'Line', 'coordinates':coords}
        elif type == "Polygon": 
            coords = [[float(coords[i+1]), float(coords[i])] for i in xrange(0, len(coords), 2)]
            return {'type':'Polygon', 'coordinates':[coords]}
        elif type == "Point":    
            coords.reverse()
            return {'type':'Point', 'coordinates':[map(float,coords)]}
        elif type == "Box":  
            coords = [[[float(coords[1]), float(coords[0])], 
                       [float(coords[3]), float(coords[0])], 
                       [float(coords[3]), float(coords[2])], 
                       [float(coords[1]), float(coords[2])], 
                       [float(coords[1]), float(coords[0])]]]  
            return {'type':'Polygon', 'coordinates':coords}
    
    def extract_entry_geometry(self, entry_dom):
        """Given an entry, do our best to extract its geometry. This has been
           designed to maximize the potential of finding geometries, but may
           not work on some features, since everyone seems to do geometries
           differently."""
        points = entry_dom.getElementsByTagName("georss:point")
        lines = entry_dom.getElementsByTagName("georss:line")
        polys = entry_dom.getElementsByTagName("georss:polygon")
        box = entry_dom.getElementsByTagName("georss:box")
        
        type = None 
        element = None
        for geom_type in ['Point', 'LineString', 'Polygon']: 
            geom = entry_dom.getElementsByTagName("gml:%s" % geom_type)
            if len(geom):
                type = geom_type
                element = geom[0]
        if type == "Point":
            points = element.getElementsByTagName("gml:pos")
        elif type == "LineString":
            lines = element.getElementsByTagName("gml:posList")
        elif type == "Polygon":
            polys = element.getElementsByTagName("gml:posList")
        
        if len(points):
            coords = points[0].firstChild.nodeValue
            geometry = self.coordinates_to_geom(coords, "Point")
            
        elif len(lines):
            coords = lines[0].firstChild.nodeValue
            geometry = self.coordinates_to_geom(coords, "Line")
            
        elif len(polys):
            coords = polys[0].firstChild.nodeValue
            geometry = self.coordinates_to_geom(coords, "Polygon")
            
        elif len(box):
            coords = box[0].firstChild.nodeValue
            geometry = self.coordinates_to_geom(coords, "Box")
        
        else:
            error = "Could not find geometry in Feature. XML was: \n\n%s" % entry_dom.toxml()
            if hasattr(self.service.datasources[self.datasource],'debug'): 
                raise Exception(error)
            else:
                print >>sys.stderr, error 
            return None   
        return geometry    
    
    def entry_to_feature(self, entry_dom):
        id = 1 
        try:
            id = entry_dom.getElementsByTagName("id")[0].firstChild.nodeValue
        except:
            id = 1
        feature = Feature(str(id))
        
        geometry = self.extract_entry_geometry(entry_dom)
        
        if not geometry: return None
        
        feature.geometry = geometry
        
        for node in entry_dom.childNodes:
            try:
                attr_name = node.tagName.split(":")[-1]
                if attr_name not in ['point', 'line', 'polygon', 'id', 'where']:
                    try:
                        feature.properties[attr_name] = node.firstChild.nodeValue
                    except:
                        pass
            except:
                pass
                
        feature.properties['timestamp'] = time.time()        
        
        return feature    
