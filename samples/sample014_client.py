#!/usr/bin/python

"""
sample014_client
"""

import sys
import logging
from pprint import pprint
from time import sleep
from random import seed, random

import urllib
import simplejson
from threading import Thread, Lock

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
my_cache = {}
cache_lock = None

#
#   MyCacheCmd
#

@bacpypes_debugging
class MyCacheCmd(ConsoleCmd):

    def do_dump(self, arg):
        """dump - nicely print the cache"""
        if _debug: MyCacheCmd._debug("do_dump %r", arg)

        cache_lock.acquire()
        pprint(my_cache)
        cache_lock.release()

    def do_set(self, arg):
        """set <key> <value> - change a cache value"""
        if _debug: MyCacheCmd._debug("do_set %r", arg)

        key, value = arg.split()

        cache_lock.acquire()
        my_cache[key] = value
        cache_lock.release()

    def do_del(self, arg):
        """del <key> - delete a cache entry"""
        if _debug: MyCacheCmd._debug("do_del %r", arg)

        try:
            cache_lock.acquire()
            del my_cache[arg]
            cache_lock.release()
        except:
            print arg, "not in cache"

#
#   MyCacheThread
#

@bacpypes_debugging
class MyCacheThread(Thread):

    def __init__(self, url):
        if _debug: MyCacheThread._debug("__init__ %r", url)
        Thread.__init__(self, name="MyCacheThread(%s)" % (url,))

        # save the url
        self.url = url
        self.go = True

        # daemonic
        self.daemon = True

        # start the thread
        self.start()

    def run(self):
        if _debug: MyCacheThread._debug("(%s) run", self.url)

        while self.go:
            nap_time = 3.0 + random() * 2
            if _debug: MyCacheThread._debug("(%s) sleeping %f", self.url, nap_time)

            sleep(nap_time)
            if _debug: MyCacheThread._debug("(%s) awake", self.url)

            try:
                urlfile = urllib.urlopen(self.url)
                if _debug: MyCacheThread._debug("(%s) urlfile: %r", self.url, urlfile)

                cache_update = simplejson.load(urlfile)
                if _debug: MyCacheThread._debug("(%s) cache_update: %r", self.url, cache_update)

                cache_lock.acquire()
                my_cache.update(cache_update)
                cache_lock.release()

                urlfile.close()
            except Exception, err:
                sys.stderr.write("(%s) exception: %r\n" % (self.url, err))

        if _debug: MyCacheThread._debug("(%s) fini", self.url)

#
#   __main__
#

try:
    if ('--buggers' in sys.argv):
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            sys.stdout.write(loggerName + '\n')
        sys.exit(0)

    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        i = indx + 1
        while (i < len(sys.argv)) and (not sys.argv[i].startswith('--')):
            ConsoleLogHandler(sys.argv[i])
            i += 1
        del sys.argv[indx:i]

    _log.debug("initialization")

    # create a lock for the cache
    cache_lock = Lock()

    # console
    MyCacheCmd()

    # build a list of update threads
    cache_threads = []
    for url in sys.argv[1:]:
        cache_thread = MyCacheThread(url)
        _log.debug("    - cache_thread: %r", cache_thread)

        cache_threads.append(cache_thread)

    _log.debug("running")

    # run until stopped
    run()

    # stop all the threads
    for cache_thread in cache_threads:
        cache_thread.go = False

    # wait for them
    sleep(5)

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
