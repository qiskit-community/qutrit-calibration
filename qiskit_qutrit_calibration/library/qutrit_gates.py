# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
EF standard randomized benchmarking.
"""

from typing import Optional

from qiskit.circuit import Gate
from qiskit.circuit.parameterexpression import ParameterValueType


class SX12Gate(Gate):
    """The single-qubit Sqrt(X) gate on EF subspace."""

    def __init__(self, label: Optional[str] = None):
        """Create new SX12 gate."""
        super().__init__("sx12", 1, [], label=label)


class SY12Gate(Gate):
    """The single-qubit Sqrt(Y) gate on EF subspace."""

    def __init__(self, label: Optional[str] = None):
        """Create new SY12 gate."""
        super().__init__("sy12", 1, [], label=label)


class RZ12Gate(Gate):
    """The single-qubit Sqrt(X) gate on EF subspace."""

    def __init__(self, phi: ParameterValueType, label: Optional[str] = None):
        """Create new RZ12 gate."""
        super().__init__("rz12", 1, [phi], label=label)


class X12Gate(Gate):
    """The single-qubit X gate on EF subspace."""

    def __init__(self, label: Optional[str] = None):
        """Create new X12 gate."""
        super().__init__("x12", 1, [], label=label)


class Y12Gate(Gate):
    """The single-qubit Y gate on EF subspace."""

    def __init__(self, label: Optional[str] = None):
        """Create new Y12 gate."""
        super().__init__("y12", 1, [], label=label)
