#!/usr/bin/python

"""
tutorial006a.py
"""

import sys
import logging
from pprint import pprint

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
my_cache = {}

#
#   MyCacheCmd
#

class MyCacheCmd(ConsoleCmd, Logging):

    def do_dump(self, arg):
        """dump - nicely print the cache"""
        if _debug: MyCacheCmd._debug("do_dump %r", arg)
        pprint(my_cache)

    def do_set(self, arg):
        """set <key> <value> - change a cache value"""
        if _debug: MyCacheCmd._debug("do_set %r", arg)

        key, value = arg.split()
        my_cache[key] = value

    def do_del(self, arg):
        """del <key> - delete a cache entry"""
        if _debug: MyCacheCmd._debug("do_del %r", arg)

        try:
            del my_cache[arg]
        except:
            print arg, "not in cache"

#
#   __main__
#

try:
    _log.debug("initialization")

    # console
    MyCacheCmd()

    _log.debug("running")

    # run until stopped
    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
