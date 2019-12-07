#!/usr/bin/python

"""
Tutorial 002 - Stacking with Debug
"""

from bacpypes.comm import Client, Server, Debug, bind

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
d = Debug("middle")
s = MyServer()

# bind them together in a stack
bind(c, d, s)

# the client is requesting something
c.request('hi')
