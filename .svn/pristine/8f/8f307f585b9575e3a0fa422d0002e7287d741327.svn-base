#!/usr/bin/python

"""
sample014_server
"""

import sys
from random import seed, choice, uniform
from time import time as _time

import SocketServer
import SimpleHTTPServer
import simplejson

# globals
var_names = [
    "spam",
    "eggs",
    ]
port = None

#
#   ValueServer
#

class ValueServer(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
        cache_update = {choice(var_names): uniform(0, 100)}

        sys.stdout.write(str(port) + ': ' + str(cache_update) + '\n')
        sys.stdout.flush()

        simplejson.dump(cache_update, self.wfile)

#
#   __main__
#

try:
    # get a port
    port = int(sys.argv[1])

    # fresh random numbers please
    seed(_time())

    # build and launch the server
    SocketServer.TCPServer(('', port), ValueServer).serve_forever()

except KeyboardInterrupt:
    pass
