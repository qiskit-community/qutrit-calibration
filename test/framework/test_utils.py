# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
Utilities to test calibration experiments
"""

from qiskit import QuantumCircuit
from qiskit.providers import Backend

from unittest import TestCase
from qiskit_qutrit_calibration.framework import utils


class TestUtilities(TestCase):
    """ Test utility functions """

    def test_format_params(self):
        value = 3.1415956
        digit = 3
        ref = 3.141
        test_result = utils.format_params(value, digit)
        self.assertEqual(ref, test_result)

    



""" Create experiments that don't run anything """

"""
Create analysis that 
"""

