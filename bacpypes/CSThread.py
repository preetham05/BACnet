#! /usr/bin/env python
#
# Filename: CSThread.py

"""
Module that wraps threads with a name and puts them in a list.  While 
threads already have a name and there is a way to get a list of the 
currently active threads (see threading.enumerate()), I needed a way to 
list of all of them to show the ones that should be running but are not.
"""

import sys
import time
import threading

# some debugging
_debug = 0

#
#   CSThread
#

gThreads = []

class Thread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self,name=name)
        self.threadName = name
        gThreads.append(self)

    def setName(self,name):
        threading.Thread.setName(self,name)
        self.threadName = name

    def getName(self):
        return self.threadName

def GetThreads():
    return gThreads

def StartThreads():
    """When applications initialize the threads have not been started,
    this function is called to start them."""
    for thread in gThreads:
        thread.start()

def HaltThreads():
    """Stop the threads, it would be nice if they could be started back up."""
    for thread in gThreads:
        thread.halt()
    time.sleep(0.100)

def DeadThreads():
    """Return a list of the names of threads that have died."""
    rslt = []
    for thread in gThreads:
        if not thread.isAlive():
            rslt.append(thread.threadName)
    return rslt
