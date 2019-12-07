#!/usr/bin/python

"""
Tutorial 001 - Clients and Servers
"""

from bacpypes.comm import Client, Server, bind

#
#   MyServer
#

class MyServer(Server):

    def indication(self, arg):
        print "working on", arg
        self.response(arg.upper())

#
#   MyClient
#

class MyClient(Client):

    def confirmation(self, pdu):
        print "thanks for the", pdu

#
#   __main__
#

# create a client and a server
c = MyClient()
s = MyServer()

# bind them together
bind(c, s)

# the client is requesting something
c.request('hi')
