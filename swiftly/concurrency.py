"""
Concurrency API for Swiftly.

Copyright 2011-2013 Gregory Holt

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__all__ = ['Concurrency']

import sys
from six.moves import queue

try:
    from eventlet import GreenPool, sleep, Timeout
except ImportError:
    GreenPool = None
    sleep = None
    Timeout = Exception


class Concurrency(object):
    """
    Convenience class to support concurrency, if Eventlet is
    available; otherwise it just performs at single concurrency.

    :param concurrency: The level of concurrency desired. Default: 10
    """

    def __init__(self, concurrency=10):
        self.concurrency = concurrency
        if self.concurrency and GreenPool:
            self._pool = GreenPool(self.concurrency)
        else:
            self._pool = None
        self._queue = queue.Queue()
        self._results = {}

    def _spawner(self, ident, func, *args, **kwargs):
        exc_type = exc_value = exc_tb = result = None
        try:
            result = func(*args, **kwargs)
        except (Exception, Timeout):
            exc_type, exc_value, exc_tb = sys.exc_info()
        self._queue.put((ident, (exc_type, exc_value, exc_tb, result)))

    def spawn(self, ident, func, *args, **kwargs):
        """
        Returns immediately to the caller and begins executing the
        func in the background. Use get_results and the ident given
        to retrieve the results of the func. If the func causes an
        exception, this exception will be caught and the
        sys.exc_info() will be returned via get_results.

        :param ident: An identifier to find the results of the func
            from get_results. This identifier can be anything unique
            to the Concurrency instance.
        :param func: The function to execute concurrently.
        :param args: The args to give the func.
        :param kwargs: The keyword args to the give the func.
        :returns: None
        """
        if self._pool:
            self._pool.spawn_n(self._spawner, ident, func, *args, **kwargs)
            sleep()
        else:
            self._spawner(ident, func, *args, **kwargs)

    def get_results(self):
        """
        Returns a dict of the results currently available. The keys
        are the ident values given with the calls to spawn. The
        values are tuples of (exc_type, exc_value, exc_tb, result)
        where:

        =========  ============================================
        exc_type   The type of any exception raised.
        exc_value  The actual exception if any was raised.
        exc_tb     The traceback if any exception was raised.
        result     If no exception was raised, this will be the
                   return value of the called function.
        =========  ============================================
        """
        try:
            while True:
                ident, value = self._queue.get(block=False)
                self._results[ident] = value
        except queue.Empty:
            pass
        return self._results

    def join(self):
        """
        Blocks until all currently pending functions have finished.
        """
        if self._pool:
            self._pool.waitall()
