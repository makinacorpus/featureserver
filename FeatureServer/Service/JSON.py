__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: JSON.py 412 2008-01-01 08:15:59Z crschmidt $"

from FeatureServer.Service import Request
from FeatureServer.Service import Action
from FeatureServer.Service import NoLayerException
from FeatureServer.Feature import Feature

try:
    import simplejson
except Exception, E:
    raise Exception("simplejson is required for using the JSON service. (Import failed: %s)" % E)

class JSON(Request):
    def __init__(self, service):
        Request.__init__(self, service)
        self.callback = None
    
    def encode_metadata(self, action):
        layers = self.service.datasources
        metadata = []
        for key in layers.keys():
            metadata.append(
              { 
                'name': key,
                'url': "%s/%s" % (self.host, key)
              }
            )
            
        result_data = {'Layers': metadata}
        
        result = simplejson.dumps(result_data) 
        if self.callback:
            result = "%s(%s);" % (self.callback, result)
        
        return ("text/plain", result)
    
    def parse(self, params, path_info, host, post_data, request_method):
        if 'callback' in params:
            self.callback = params['callback']
        try:
            self.get_layer(path_info, params) 
        except NoLayerException:
            action = Action()
            action.method = "metadata"
            self.host = host
            self.actions.append(action)
            return 
        Request.parse(self, params, path_info, host, post_data, request_method)    
    
    def createFeature(self, feature_dict, id = None):
        feature = Feature(id)
        if feature_dict.has_key('geometry'):
            feature.geometry = feature_dict['geometry']
        if feature_dict.has_key('properties'):
            feature.properties = feature_dict['properties']
        return feature 
        
    
    def encode(self, result):
        results = []
        for action in result:
            for i in action:
                data = i.to_dict()
                for key,value in data['properties'].items():
                    if value and isinstance(value, str): 
                        data['properties'][key] = unicode(value,"utf-8")
                results.append(data)
        
        result_data = {'features': results}
        
        result = simplejson.dumps(result_data) 
        
        if self.datasource:
            datasource = self.service.datasources[self.datasource]
        
        if self.callback and datasource and hasattr(datasource, 'gaping_security_hole'):
            return ("text/plain", "%s(%s);" % (self.callback, result))
        else:    
            return ("text/plain", result)
    
    def handle_post(self, params, path_info, host, post_data, request_method):
            actions = []
            
            id = self.get_id_from_path_info(path_info)
            if id:
                action = Action()
                action.method = "update"
                action.id = id 
                try:
                        feature_dict = simplejson.loads(post_data)
                except: 
                        raise Exception("Invalid JSON. Content was: %s" % post_data)
                if feature_dict.has_key("features"):
                    feature_dict = feature_dict['features'][0]
                elif feature_dict.has_key("members"):
                    feature_dict = feature_dict['members'][0]
                feature = self.createFeature(feature_dict, action.id)
                action.feature = feature
                actions.append(action)
            
            else:
                feature_data = simplejson.loads(post_data)
                if feature_data.has_key("features"):
                    feature_data = feature_data['features']
                elif feature_data.has_key("members"):
                    feature_data = feature_data['members']
                else:
                    feature_data = [feature_data]
                for feature in feature_data:
                    action = Action()
                    action.method = "create"
                    action.feature = self.createFeature(feature)
                    actions.append(action)
                
            return actions
