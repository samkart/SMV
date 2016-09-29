import unittest

from smvbasetest import SmvBaseTest

import pyspark
from pyspark.context import SparkContext
from pyspark.sql import SQLContext, HiveContext
from pyspark.sql.functions import col

class DfHelperTest(SmvBaseTest):
    def test_selectPlus(self):
        df = self.createDF("k:String;v:Integer", "a,1;b,2")
        r1 = df.selectPlus((col('v') + 1).alias("v2"))
        expect = self.createDF("k:String;v:Integer;v2:Integer", "a,1,2;b,2,3")
        self.should_be_same(expect, r1)

    def test_smvGroupBy(self):
        return "TODO implement"

    def test_dedupByKey(self):
        schema = "a:Integer; b:Double; c:String"
        df = self.createDF(
            schema,
            """1,2.0,hello;
            1,3.0,hello;
            2,10.0,hello2;
            2,11.0,hello3"""
        )
        r1 = df.dedupByKey("a")
        expect = self.createDF(
            schema,
            """1,2.0,hello;
            2,10.0,hello2"""
        )
        self.should_be_same(expect, r1)

class ColumnHelperTest(unittest.TestCase):
    def test_smvMonth(self):
        return "TODO implement"