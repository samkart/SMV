from smv import *

from org.tresamigos.smvtest.test5 import input

class M1(SmvModule, SmvOutput):
    def requiresDS(self):
        return [input.table]

    def run(self, i):
        return i[input.table]
