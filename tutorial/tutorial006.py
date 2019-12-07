#!/usr/bin/python

"""
tutorial006.py
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   __main__
#

try:
    _log.debug("initialization")

    # console
    ConsoleCmd()

    _log.debug("running")

    # run until stopped
    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
