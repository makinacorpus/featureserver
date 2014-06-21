#!/usr/bin/python

"""A simple, standalone web server that serves FeatureServer requests."""

__author__  = "MetaCarta"
__version__ = "FeatureServer $Id: featureserver_http_server.py 404 2007-12-31 14:48:44Z crschmidt $"
__license__ = "Clear BSD"
__copyright__ = "2006-2007 MetaCarta"


from optparse import OptionParser
from FeatureServer.Server import wsgiApp

def run(port=8080, thread=False):
    from wsgiref import simple_server
    if thread:
        from SocketServer import ThreadingMixIn
        class myServer(ThreadingMixIn, simple_server.WSGIServer):
            pass 
    else:
        class myServer(simple_server.WSGIServer):
            pass

    httpd = myServer(('',port), simple_server.WSGIRequestHandler,)
    httpd.set_app(wsgiApp)
    
    try:
        print "Listening on port %s" % port
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "Shutting down."

if __name__ == '__main__':
    parser = OptionParser(version=__version__, description=__doc__)
    parser.add_option("-p", "--port", 
        help="port to run webserver on. Default is 8080", 
        dest="port", 
        action='store', 
        type="int", 
        default=8080)
    parser.add_option("-t", help="enable threading in HTTP Server.", dest="thread", action="store_true", default=False)    

    (options, args) = parser.parse_args()
    run(options.port, options.thread)


