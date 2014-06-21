#!/usr/bin/python

__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: Server.py 443 2008-03-18 15:03:27Z crschmidt $"

import sys
import cgi
import time
import os
import traceback
import ConfigParser

# Windows doesn't always do the 'working directory' check correctly.
if sys.platform == 'win32':
    workingdir = os.path.abspath(os.path.join(os.getcwd(), os.path.dirname(sys.argv[0])))
    cfgfiles = (os.path.join(workingdir, "featureserver.cfg"), os.path.join(workingdir,"..","featureserver.cfg"))
else:
    cfgfiles = ("featureserver.cfg", os.path.join("..", "featureserver.cfg"), "/etc/featureserver.cfg")


class Server (object):
    """The server manages the datasource list, and does the management of
       request input/output.  Handlers convert their specific internal
       representation to the parameters that dispatchRequest is expecting,
       then pass off to dispatchRequest. dispatchRequest turns the input 
       parameters into a (content-type, response string) tuple, which the
       servers can then return to clients. It is possible to integrate 
       FeatureServer into another content-serving framework like Django by
       simply creating your own datasources (passed to the init function) 
       and calling the dispatchRequest method. The Server provides a classmethod
       to load datasources from a config file, which is the typical lightweight
       configuration method, but does use some amount of time at script startup.
       """ 
       
    def __init__ (self, datasources, metadata = {}):
        self.datasources   = datasources
        self.metadata      = metadata
    
    def _loadFromSection (cls, config, section, module_type, **objargs):
        type  = config.get(section, "type")
        module = __import__("%s.%s" % (module_type, type), globals(), locals(), type)
        objclass = getattr(module, type)
        for opt in config.options(section):
            if opt != "type":
                objargs[opt] = config.get(section, opt)
        if module_type is 'DataSource':
            return objclass(section, **objargs)
        else:
            return objclass(**objargs)
    loadFromSection = classmethod(_loadFromSection)

    def _load (cls, *files):
        """Class method on Service class to load datasources
           and metadata from a configuration file."""
        config = ConfigParser.ConfigParser()
        config.read(files)
        
        metadata = {}
        if config.has_section("metadata"):
            for key in config.options("metadata"):
                metadata[key] = config.get("metadata", key)

        datasources = {}
        for section in config.sections():
            if section == "metadata": continue
            datasources[section] = cls.loadFromSection(
                                    config, section, 'DataSource')

        return cls(datasources, metadata)
    load = classmethod(_load)


    def dispatchRequest (self, params, path_info, host, post_data = None, request_method = "GET", requested_content_types = ""):
        """Read in request data, and return a (content-type, response string) tuple. May
           raise an exception, which should be returned as a 500 error to the user."""  
        response_code = "200 OK"
        request = None
        content_types = {
          'application/vnd.google-earth.kml+xml': 'KML',
          'application/json': 'JSON',
          'text/javascript': 'JSON',
          'application/rss+xml': 'GeoRSS',
          'text/html': 'HTML',
          'osm': 'OSM',
          'gml': 'WFS',
          'wfs': 'WFS',
          'kml': 'KML',
          'json': 'JSON',
          'georss': 'GeoRSS',
          'atom': 'GeoRSS',
          'html': 'HTML',
          'geojson':'GeoJSON'
        }  
        
        path = path_info.split("/")
        
        found = False
        
        format = ""
        if params.has_key("format"):
            format = params['format']
            if format.lower() in content_types:
                format = content_types[format.lower()]
                found = True
        
        if not found and len(path) > 1:
            path_pieces = path[-1].split(".")
            if len(path_pieces) > 1:
                format = path_pieces[-1]
                if format.lower() in content_types:
                    format = content_types[format.lower()]
                    found = True
        
        if not found and requested_content_types:
           if requested_content_types.lower() in content_types:
               format = content_types[requested_content_types.lower()]
               found = True
        
        if not found and not format:
            if self.metadata.has_key("default_service"):
                format = self.metadata['default_service']
            else:    
                format = "JSON"
                
        service_module = __import__("Service.%s" % format, globals(), locals(), format)
        service = getattr(service_module, format)
        request = service(self)
            
        response = []
        
        request.parse(params, path_info, host, post_data, request_method)
        
        # short circuit datasource where the first action is a metadata request. 
        if len(request.actions) and request.actions[0].method == "metadata": 
            return request.encode_metadata(request.actions[0])
        
        datasource = self.datasources[request.datasource] 
        
        datasource.begin()
        try:
            for action in request.actions:
                method = getattr(datasource, action.method)
                result = method(action)
                response.append(result) 
            datasource.commit()
        except:
            datasource.rollback()
            raise

        return request.encode(response)
        
def modPythonHandler (apacheReq, service):
    """Mod Python handler reads data from an apache request
       and passes it into dispatchRequest."""
    from mod_python import apache, util
    try:
        
        if apacheReq.headers_in.has_key("X-Forwarded-Host"):
            host = "http://" + apacheReq.headers_in["X-Forwarded-Host"]
        else:
            host = "http://" + apacheReq.headers_in["Host"]
        host += apacheReq.uri
        
        accepts = "" 
        if apacheReq.headers_in.has_key("Accept"):
            accepts = apacheReq.headers_in["Accept"]
        elif apacheReq.headers_in.has_key("Content-Type"):
            accepts = apacheReq.headers_in["Content-Type"]
        
        post_data = apacheReq.read()
        request_method = apacheReq.method

        params = {}
        if request_method != "POST":
            fs = util.FieldStorage(apacheReq) 
            for key in fs.keys():
                params[key.lower()] = fs[key] 
       
        format, content = service.dispatchRequest( 
                                params, 
                                apacheReq.path_info,
                                host,
                                post_data, 
                                request_method
                                )
        apacheReq.content_type = format
        apacheReq.send_http_header()
        content = content.encode("utf-8")
        apacheReq.write(content)
    except Exception, E:
        apacheReq.content_type = "text/plain"
        apacheReq.status = apache.HTTP_INTERNAL_SERVER_ERROR
        apacheReq.send_http_header()
        error = "An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback)))
        apacheReq.write(error)

        if service and service.metadata.has_key("error_log"):
            f = open(service.metadata['error_log'], "a")
            f.write(error)
            f.close()
        else: 
            print >>sys.stderr, error
    return apache.OK

def wsgiHandler (environ, start_response, service):
    """wsgiHandler reads data from a wsgi request. Uses paste.reques
       parse_formvars method."""
    try:
        from paste.request import parse_formvars
        request_method = hpath_info = host = post_data = ""
        params = {}

        request_method = environ['REQUEST_METHOD']
        
        if request_method != "GET" and request_method != "DELETE":
            post_data = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        else:
            fields = parse_formvars(environ)
            for key in fields.keys():
                params[key.lower()] = fields[key] 

        if "PATH_INFO" in environ: 
            path_info = environ["PATH_INFO"]

        if "HTTP_X_FORWARDED_HOST" in environ:
            host      = "http://" + environ["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in environ:
            host      = "http://" + environ["HTTP_HOST"]

        host += environ["SCRIPT_NAME"]

        accepts = ""
        if environ.has_key("CONTENT_TYPE"):
            accepts = environ['CONTENT_TYPE']
        else:
            accepts = environ['HTTP_ACCEPT']

        format, content = service.dispatchRequest( params, path_info, host, post_data, request_method, accepts )
        content = content.encode("utf-8")
        start_response("200 OK", [('Content-Type',format)])
        return [content]

    except Exception, E:
        start_response("500 Internal Server Error", [('Content-Type','text/plain')])
        error = ["An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback)))]
        if service and service.metadata.has_key("error_log"):
            f = open(service.metadata['error_log'], "a")
            f.write(error[0])
            f.close()
        else: 
            print >>sys.stderr, error[0] 
        return error

def cgiHandler (service = None):
    """cgiHandler used to create a CGI endpoint.""" 
    try:
        if not service:
            service = Server.load(*cfgfiles)
        params = {}
        
        request_method = os.environ["REQUEST_METHOD"]
        accepts = "" 
        if "CONTENT_TYPE" in os.environ:
            accepts = os.environ['CONTENT_TYPE']
        elif "HTTP_ACCEPT" in os.environ:
            accepts = os.environ['HTTP_ACCEPT']

        post_data = None 
        if request_method != "GET" and request_method != "DELETE":
            post_data = sys.stdin.read()
        
        input = cgi.FieldStorage()
        try:
            for key in input.keys(): params[key.lower()] = input[key].value
        except TypeError:
            pass

        path_info = host = ""

        if "PATH_INFO" in os.environ: 
            path_info = os.environ["PATH_INFO"]

        if "HTTP_X_FORWARDED_HOST" in os.environ:
            host      = "http://" + os.environ["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in os.environ:
            host      = "http://" + os.environ["HTTP_HOST"]

        host += os.environ["SCRIPT_NAME"]

        

        format, content = service.dispatchRequest( params, path_info, host, post_data, request_method, accepts )
        print "Content-type: %s\n" % format

        print content.encode("utf-8")
    except Exception, E:
        print "Cache-Control: max-age=10, must-revalidate" # make the client reload        
        print "Content-type: text/plain\n"
        error = "An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback)))
        print error
        
        if service and service.metadata.has_key("error_log"):
            f = open(service.metadata['error_log'], "a")
            f.write(error)
            f.close()
        else: 
            print >>sys.stderr, error

theServer = None

def handler (apacheReq):
    global theServer
    options = apacheReq.get_options()
    cfgs    = cfgfiles
    if options.has_key("FeatureServerConfig"):
        cfgs = (options["FeatureServerConfig"],) + cfgs
    if not theServer:
        theServer = Server.load(*cfgs)
    return modPythonHandler(apacheReq, theServer)

def wsgiApp (environ, start_response):
    global theServer
    cfgs    = cfgfiles
    if not theServer:
        theServer = Server.load(*cfgs)
    return wsgiHandler(environ, start_response, theServer)


if __name__ == '__main__':
    cgiHandler()
