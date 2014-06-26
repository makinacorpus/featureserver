__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: GeoJSON.py 412 2008-01-01 08:15:59Z crschmidt $"

from FeatureServer.Service import Request, Action 
from FeatureServer.Service.JSON import JSON
from FeatureServer.Feature import Feature

try:
    import simplejson
except Exception, E:
    raise Exception("simplejson is required for using the GeoJSON service. (Import failed: %s)" % E)

class GeoJSON(JSON):
    def createFeature(self, feature_dict, id = None):
        feature = Feature(id)
        if feature_dict.has_key('geometry'):
            feature.geometry = feature_dict['geometry']
            if feature.geometry['type'] == "Point":
                feature.geometry['coordinates'] = [feature.geometry['coordinates']] 
            if feature.geometry['type'] == "LineString":
                feature.geometry['type'] = "Line"
        if feature_dict.has_key('properties'):
            feature.properties = feature_dict['properties']
        return feature 
        
    
    def encode(self, result):
        results = []
        result_data = None
        for action in result:
            for i in action:
                data = self.encode_feature(i)
                for key,value in data['properties'].items():
                    if value and isinstance(value, str): 
                        data['properties'][key] = unicode(value,"utf-8")
                results.append(data)
        
        result_data = {'type':'FeatureCollection','features': results,
                       'crs':{  'type':'none',
                                'properties':{'info':'No CRS information has been provided with this data.'} 
                             } 
                      }
        
        result = simplejson.dumps(result_data) 
        
        if self.callback:
            return ("text/plain", "%s(%s);" % (self.callback, result))
        else:    
            return ("text/plain", result)
    
    def encode_feature(self, feature):
        feat = {"id": feature.id, "geometry": feature.geometry, "properties": feature.properties, 'type':"Feature"}
        if feat['geometry']['type'] == "Point":
            feat['geometry']['coordinates'] = feat['geometry']['coordinates'][0]
        if feat['geometry']['type'] == "Line":
            feat['geometry']['type'] = "LineString"
        return feat    
