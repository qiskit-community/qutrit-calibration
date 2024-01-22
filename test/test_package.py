# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""qiskit_qutrit_calibration package test"""


"""
##### FEATURES TO TEST #####

Each set of test data should include:
    - Circuits that will be executed
    - An example job ExperimentData set that will be used for analysis

1. Instantiating a QutritCalibration object from a backend
2. Perform Rough Frequency calibration with test data
3. Perform Rough Amplitude calibration with test data that has a single and double peak
4. Perform Narrow Band Spectroscopy experiment on test data
5. Perform Rought DRAG experiment
6. Perform Fine Amplitude experiment
7. Perform Standard & Polar Randomized Benchmarking
8. File I/O for experiment/calibration data 
9. Create calibrated single qutrit gates to execute based on calibrations

"""
#import unittest
from unittest import TestCase


class TestPackage(TestCase):
    """This contains tests that the auto generated package"""

    def test_package_import(self):
        """Test package can be imported successfully"""
        try:
            # pylint: disable = unused-import
            import qiskit_qutrit_calibration

            version = qiskit_qutrit_calibration.__version__
            self.assertTrue(version)

        # pylint: disable = broad-except
        except Exception as ex:
            self.fail(f"Failed to import package. Import raised exception {ex}")

