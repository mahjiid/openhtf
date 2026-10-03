# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for test_descriptor module."""

import re
from unittest import mock

from absl.testing import parameterized
from openhtf.core import test_descriptor
from openhtf.util import configuration

CONF = configuration.CONF


class RegexMatcher(object):

  def __init__(self, pattern):
    self.pattern = pattern

  def __eq__(self, other):
    return re.search(self.pattern, other) is not None


class TestTest(parameterized.TestCase):

  @mock.patch.object(test_descriptor, '_LOG')
  def test_output_cb_error_stacktrace_log(self, mock_log):

    def phase():
      return

    def callback(test_record):
      del test_record
      raise Exception('test123')

    test = test_descriptor.Test(phase)
    test.add_output_callbacks(callback)
    test.execute()
    mock_log.error.assert_called_once_with(
        mock.ANY, callback, RegexMatcher(r'test_descriptor_test(.|\n)*test123'))

  def test_output_cb_error_can_fail_test(self):

    def phase():
      return

    observed_records = []

    def failing_callback(test_record):
      del test_record
      raise RuntimeError('storage unavailable')

    def observe_callback(test_record):
      observed_records.append(test_record)

    test = test_descriptor.Test(phase)
    test.configure(fail_on_output_callback_exception=True)
    test.add_output_callbacks(failing_callback, observe_callback)

    self.assertFalse(test.execute())
    self.assertLen(observed_records, 1)
    record = observed_records[0]
    self.assertEqual(record.outcome.name, 'FAIL')
    self.assertLen(record.outcome_details, 1)
    self.assertEqual(record.outcome_details[0].code, 'OUTPUT_CALLBACK_ERROR')
    self.assertIn('failing_callback', record.outcome_details[0].description)
    self.assertIn('storage unavailable', record.outcome_details[0].description)

  def test_output_cb_error_default_keeps_outcome(self):

    def phase():
      return

    observed_records = []

    def failing_callback(test_record):
      del test_record
      raise RuntimeError('storage unavailable')

    def observe_callback(test_record):
      observed_records.append(test_record)

    test = test_descriptor.Test(phase)
    test.add_output_callbacks(failing_callback, observe_callback)

    self.assertTrue(test.execute())
    self.assertLen(observed_records, 1)
    self.assertEqual(observed_records[0].outcome.name, 'PASS')
    self.assertEmpty(observed_records[0].outcome_details)

  @parameterized.named_parameters([
      {
          'testcase_name': 'trigger_none_capture_source_false',
          'test_start': None,
          'capture_source': False,
      },
      {
          'testcase_name': 'trigger_none_capture_source_true',
          'test_start': None,
          'capture_source': True,
      },
      {
          'testcase_name': 'trigger_lambda_capture_source_false',
          'test_start': lambda: 'DUT_ID',
          'capture_source': False,
      },
      {
          'testcase_name': 'trigger_lambda_capture_source_true',
          'test_start': lambda: 'DUT_ID',
          'capture_source': True,
      },
  ])
  @CONF.save_and_restore
  def test_execute(self, test_start, capture_source):
    CONF.load(capture_source=capture_source)

    def phase():
      """No-op phase for testing."""

    test = test_descriptor.Test(phase)
    self.assertTrue(test.execute(test_start=test_start))
