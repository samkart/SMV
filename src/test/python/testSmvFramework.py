#
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

import unittest
import json

from test_support.smvbasetest import SmvBaseTest
from smv import *
import smv.utils
from smv.dqm import *
from smv.error import SmvDqmValidationError

import pyspark
from pyspark.context import SparkContext
from pyspark.sql import SQLContext, HiveContext
from pyspark.sql.functions import col, lit
from py4j.protocol import Py4JJavaError


class SmvFrameworkTest(SmvBaseTest):
    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.stages=stage']

    def test_SmvDQM(self):
        fqn = "stage.modules.D3"

        msg = """{"passed":false,"dqmStateSnapshot":{"totalRecords":3,"parseError":{"total":0,"firstN":[]},"fixCounts":{"a_lt_1_fix":1},"ruleErrors":{"b_lt_03":{"total":1,"firstN":["org.tresamigos.smv.dqm.DQMRuleError: b_lt_03 @FIELDS: b=0.5"]}}},"errorMessages":[{"FailTotalRuleCountPolicy(2)":"true"},{"FailTotalFixCountPolicy(1)":"false"},{"FailParserCountPolicy(1)":"true"}],"checkLog":["Rule: b_lt_03, total count: 1","org.tresamigos.smv.dqm.DQMRuleError: b_lt_03 @FIELDS: b=0.5","Fix: a_lt_1_fix, total count: 1"]}"""

        with self.assertRaises(SmvDqmValidationError) as cm:
            df = self.df(fqn)
            df.smvDumpDF()
        
        e = cm.exception
        self.assertEqual(e.dqmValidationResult["passed"], False)
        self.assertEqual(e.dqmValidationResult["dqmStateSnapshot"]["totalRecords"], 3)
        self.assertEqual(e.dqmValidationResult["dqmStateSnapshot"]["parseError"]["total"],0)
        self.assertEqual(e.dqmValidationResult["dqmStateSnapshot"]["fixCounts"]["a_lt_1_fix"],1)
        self.assertEqual(e.dqmValidationResult["dqmStateSnapshot"]["ruleErrors"]["b_lt_03"]["total"],1)

    # All SmvInput related tests were moved to testSmvInput.py
    #TODO: add other SmvDataSet unittests

class SmvRunConfigTest1(SmvBaseTest):

    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.config.s=s1', 'smv.config.i=1', 'smv.config.b=True', 'smv.stages=stage',
                '-m', "None"]

    def test_SmvCsvStringData_with_SmvRunConfig(self):
        fqn = "stage.modules.D4"
        df = self.df(fqn)
        expect = self.createDF("a: String;b: Integer",
            """test1_s1,1;
                test2_not_i2,4;
                test3_b,5;
                test4_undefined_c,7;
                test5_undefined_one,9;
                test6_undefined_bool,11""")
        self.should_be_same(expect, df)

class SmvRunConfigTest2(SmvBaseTest):

    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.config.s=s2', 'smv.config.i=2', 'smv.config.b=false', 'smv.config.c=c',
                'smv.config.one=1', 'smv.config.bool=True', 'smv.stages=stage', '-m', "None"]

    def test_SmvCsvStringData_with_SmvRunConfig(self):
        fqn = "stage.modules.D4"
        df = self.df(fqn)
        expect = self.createDF("a:String;b:Integer",
            """test1_not_s1,2;
                test2_i2,3;
                test3_not_b,6;
                test4_defined_c,8;
                test5_defined_one,10;
                test6_defined_bool,12""")
        self.should_be_same(expect, df)

class SmvNameErrorPropagationTest(SmvBaseTest):
    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.stages=stage', '-m', "None"]

    def test_module_NameError_propagation(self):
        fqn = "stage.modules.ModWithBadName"
        with self.assertRaisesRegexp(Py4JJavaError, "NameError"):
            self.df(fqn)


class SmvSyntaxErrorPropagationTest(SmvBaseTest):
    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.stages=syntax_error_stage', '-m', "None"]

    def test_module_SyntaxError_propagation(self):
        fqn = "syntax_error_stage.modules.ModWithBadSyntax"
        with self.assertRaisesRegexp(Py4JJavaError, "SyntaxError"):
            self.df(fqn)

# TODO: this should be moved into own file.
class SmvMetadataTest(SmvBaseTest):
    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.stages=metadata_stage', '-m', "None"]

    def test_metadata_includes_user_metadata(self):
        fqn = "metadata_stage.modules.ModWithUserMeta"
        self.df(fqn)
        with open(self.tmpDataDir() + "/history/{}.hist/part-00000".format(fqn)) as f:
            metadata_list = json.loads(f.read())
            metadata = metadata_list['history'][0]
        self.assertEqual(metadata['foo'], "bar")

    def test_metadata_validation_failure_causes_error(self):
        fqn = "metadata_stage.modules.ModWithFailingValidation"
        with self.assertRaisesRegexp(Py4JJavaError, "SmvMetadataValidationError"):
            self.df(fqn)

    def test_invalid_metadata_rejected_gracefully(self):
        fqn = "metadata_stage.modules.ModWithInvalidMetadata"
        with self.assertRaisesRegexp(Exception, r"metadata .* is not a dict"):
            self.df(fqn)

    def test_invalid_metadata_validation_rejected_gracefully(self):
        fqn = "metadata_stage.modules.ModWithInvalidMetadataValidation"
        with self.assertRaisesRegexp(Exception, r"message .* is not a string"):
            self.df(fqn)

    def test_metadata_only_called_once(self):
        # running the module will incr the global metadata count by 1 for each
        # call to metadata
        fqn = "metadata_stage.modules.ModWithMetaCount"
        self.df(fqn)

        # Note: must import AFTER `df` above to get latest instance of package!
        from metadata_stage.modules import metadata_count
        self.assertEqual(metadata_count, 1)

class SmvNeedsToRunTest(SmvBaseTest):
    @classmethod
    def smvAppInitArgs(cls):
        return ['--smv-props', 'smv.stages=stage']

    @classmethod
    def load(cls, fqn):
        urn = "mod:" + fqn
        return cls.smvApp.j_smvPyClient.loadSingleUrn(urn)

    @classmethod
    def deleteModuleOutput(cls, j_m):
        cls.smvApp.j_smvPyClient.deleteModuleOutput(j_m)

    def test_input_module_does_not_need_to_run(self):
        fqn = "stage.modules.CsvFile"
        j_m = self.load(fqn)
        self.assertFalse(j_m.needsToRun())

    def test_module_not_persisted_should_need_to_run(self):
        fqn = "stage.modules.NeedRunM1"
        j_m = self.load(fqn)
        self.deleteModuleOutput(j_m)
        self.assertTrue(j_m.needsToRun())

    def test_module_persisted_should_not_need_to_run(self):
        fqn = "stage.modules.NeedRunM1"
        # Need to force run, since the df might in cache while the persisted file get deleted
        self.df(fqn, forceRun=True)
        self.assertFalse(self.load(fqn).needsToRun())

    def test_module_depends_on_need_to_run_module_also_need_to_run(self):
        fqn = "stage.modules.NeedRunM2"
        fqn0 = "stage.modules.NeedRunM1"
        self.df(fqn, True)
        self.deleteModuleOutput(self.load(fqn0)) # deleting persist files made M1 need to run
        self.assertTrue(self.load(fqn).needsToRun())

    def test_ephemeral_module_depends_on_not_need_to_run_also_not(self):
        fqn = "stage.modules.NeedRunM3"
        fqn0 = "stage.modules.NeedRunM1"
        self.df(fqn0, True)
        self.assertFalse(self.load(fqn).needsToRun())

    def test_ephemeral_module_depends_on_need_to_run_also_need(self):
        fqn = "stage.modules.NeedRunM3"
        fqn0 = "stage.modules.NeedRunM1"
        self.df(fqn, True)
        self.deleteModuleOutput(self.load(fqn0)) # deleting persist files made M1 need to run
        self.assertTrue(self.load(fqn).needsToRun())
