# This file is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from collections import OrderedDict
import sys

if sys.version_info >= (3, 0):
    import queue
else:
    import Queue as queue

class ModulesVisitor(object):
    """Provides way to do depth and breadth first visit to the sub-graph
        of modules given a set of roots
    """
    def __init__(self, roots):
        self.queue = self._build_queue(roots)

    def _build_queue(self, roots):
        """Create a depth first queue with order for multiple roots"""

        # to traversal the graph in bfs order
        _working_queue = queue.Queue()
        for m in roots:
            _working_queue.put(m)

        # keep a distinct sorted list of nodes with root always in front of leafs
        _sorted = OrderedDict()
        for m in roots:
            _sorted.update({m: True})

        while(not _working_queue.empty()):
            mod = _working_queue.get()
            for m in mod.resolvedRequiresDS:
                # regardless whether seen before, add to queue, so not drop 
                # any dependency which may change the ordering of the result
                _working_queue.put(m)

                # if in the result list already, remove the old, add the new, 
                # to make sure leafs always later
                if (m in _sorted):
                    _sorted.pop(m)
                _sorted.update({m: True})

        # reverse the result before output to make leafs first
        return [m for m in reversed(_sorted)]

    def dfs_visit(self, action, state):
        """Depth first visit"""
        for m in self.queue:
            action(m, state)
    
    def bfs_visit(self, action, state):
        """Breadth first visit"""
        for m in reversed(self.queue):
            action(m, state)
