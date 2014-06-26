#!/usr/bin/python
from FeatureServer.Server import wsgiApp

import sys

if __name__ == '__main__':
    from flup.server.fcgi_fork  import WSGIServer
    WSGIServer(wsgiApp).run()
