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
import cmath
import math
from abc import abstractmethod
from typing import Sequence, List, Tuple, Optional

import numpy as np
from numpy.random import Generator
from qiskit.circuit import (
    QuantumCircuit,
    QuantumRegister,
    ClassicalRegister,
    Measure,
)
from qiskit.circuit.library import XGate
from qiskit.providers import Backend, BackendV2
from qiskit.quantum_info import random_clifford, Clifford
from qiskit.transpiler import StagedPassManager, PassManager, Layout, CouplingMap
from qiskit.transpiler.passes import (
    SetLayout,
    EnlargeWithAncilla,
    FullAncillaAllocation,
    ApplyLayout,
)
from qiskit_experiments.framework import BaseExperiment, Options
from qiskit_experiments.library.randomized_benchmarking.rb_analysis import RBAnalysis
from scipy.linalg import det

from qiskit_qutrit_calibration.framework import QutritCalibrations, schedule_qutrit_circuit
from .qutrit_gates import SX12Gate, RZ12Gate, X12Gate


class BaseEFRB1Q(BaseExperiment):
    """Base class for the 1Q qutrit RB."""

    def __init__(
        self,
        physical_qubits: Tuple[int, ...],
        calibrations: QutritCalibrations,
        backend: Optional[Backend] = None,
    ):
        """Initialize an experiment.

        Args:
            physical_qubits: A physical qubits for the experiment.
            backend: The backend to run the experiment on.
        """
        super().__init__(
            physical_qubits=physical_qubits,
            analysis=RBAnalysis(),
            backend=backend,
        )
        self.calibrations = calibrations
        self._setup()

    def _setup(self):
        self.analysis.set_options(
            outcome="0", gate_error_ratio=None,
        )
        self.analysis.plotter.set_figure_options(
            xlabel="Clifford Length",
            ylabel="Survival Probability",
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            lengths=None,
            min_length=1,
            max_length=100,
            num_length=15,
            num_samples=5,
            seed=123,
        )

        return options

    @classmethod
    def _default_run_options(cls) -> Options:
        """Default options values for the experiment :meth:`run` method."""
        options = Options()
        options.use_measure_esp = False
        options.shots = 1024
        options.rep_delay = 300e-6

        return options

    def set_transpile_options(self, **fields):
        raise RuntimeError(f"{self.__class__.__name__} doesn't relay on Qiskit transpiler.")

    @abstractmethod
    def _generate_sequence(self, length: int, rng: Generator) -> Sequence[float]:
        """A helper function to return random gate sequence generator."""
        pass

    @abstractmethod
    def _sequence_to_instructions(self, *params):
        """A helper function to translate single gate element to basis gate sequence.

        This overrules standard Qiskit transpile protocol and immediately
        apply hard-coded decomposition with respect to the backend basis gates.
        Note that this decomposition ignores global phase.
        """
        pass

    def circuits(self) -> List[QuantumCircuit]:
        """Return a list of experiment circuits.

        Returns:
            A list of :class:`QuantumCircuit`.
        """
        opt = self.experiment_options
        rng = np.random.default_rng(seed=opt.seed)

        if opt.lengths is None:
            lengths = np.linspace(opt.min_length, opt.max_length, opt.num_length, dtype=int)
        else:
            lengths = opt.lengths

        qregs = QuantumRegister(1, name="q")
        cregs = ClassicalRegister(1, name="c")
        qubit = qregs[0]
        clbit = cregs[0]
        exp_circs = []
        for sample_ind in range(opt.num_samples):
            for length in lengths:
                rb_circ = QuantumCircuit(qregs, cregs)
                rb_circ.metadata = {
                    "xval": length,
                    "sample": sample_ind,
                }
                rb_circ._append(XGate(), [qubit], [])
                for params in self._generate_sequence(length, rng):
                    for inst in self._sequence_to_instructions(*params):
                        rb_circ._append(inst, [qubit], [])
                    rb_circ.barrier()
                rb_circ._append(XGate(), [qubit], [])
                rb_circ._append(Measure(), [qubit], [clbit])
                exp_circs.append(rb_circ)

        return exp_circs

    def _transpiled_circuits(self):
        virtual_circuits = self.circuits()
        initial_layout = Layout.from_intlist(self.physical_qubits, *virtual_circuits[0].qregs)
        coupling_map = CouplingMap(self._backend_data.coupling_map)

        transpiler = StagedPassManager(stages=["layout"])
        transpiler.layout = PassManager([
            SetLayout(initial_layout),
            FullAncillaAllocation(coupling_map),
            EnlargeWithAncilla(),
            ApplyLayout(),
        ])

        # Transpile
        transpiled_circuits = transpiler.run(virtual_circuits)

        exp_circs = []
        for transpiled_circuit in transpiled_circuits:
            exp_circs.append(
                schedule_qutrit_circuit(
                    circuit=transpiled_circuit,
                    qubit_index=self.physical_qubits,
                    calibrations=self.calibrations,
                    meas_map=self._backend.configuration().meas_map,
                    is_v2=isinstance(self._backend, BackendV2),
                )
            )

        return exp_circs


class EFStandardRB1Q(BaseEFRB1Q):
    """Standard randomized benchmarking for single qutrit Clifford circuit."""

    def _generate_sequence(self, length: int, rng: Generator):
        """A helper function to return random Clifford sequence generator."""
        composed = Clifford([[1, 0], [0, 1]])
        for _ in range(length):
            elm = random_clifford(1, rng)
            composed = composed.compose(elm)
            yield self._to_parameters(elm)
        if length > 0:
            yield self._to_parameters(composed.adjoint())

    @staticmethod
    def _to_parameters(elm: Clifford):
        mat = elm.to_matrix()

        su_mat = det(mat) ** (-0.5) * mat
        theta = 2 * math.atan2(abs(su_mat[1, 0]), abs(su_mat[0, 0]))
        phiplambda2 = cmath.phase(su_mat[1, 1])
        phimlambda2 = cmath.phase(su_mat[1, 0])
        phi = phiplambda2 + phimlambda2
        lam = phiplambda2 - phimlambda2

        return theta, phi, lam

    def _sequence_to_instructions(self, theta, phi, lam):
        """Single qubit Clifford decomposition with fixed number of physical gates.

        This overrules standard Qiskit transpile protocol and immediately
        apply hard-coded decomposition with respect to the backend basis gates.
        Note that this decomposition ignores global phase.
        """
        return [
            RZ12Gate(lam),
            SX12Gate(),
            RZ12Gate(theta + math.pi),
            SX12Gate(),
            RZ12Gate(phi - math.pi),
        ]


class EFPolarRB1Q(BaseEFRB1Q):

    def _generate_sequence(self, length: int, rng: Generator):
        """A helper function to return random Clifford sequence generator."""
        for _ in range(length):
            angle1, angle2 = rng.uniform(-np.pi, np.pi, 2)
            yield angle1, angle2

    def _sequence_to_instructions(self, angle1, angle2):
        """Single qubit Clifford decomposition with fixed number of physical gates.

        This overrules standard Qiskit transpile protocol and immediately
        apply hard-coded decomposition with respect to the backend basis gates.
        Note that this decomposition ignores global phase.
        """
        return [
            RZ12Gate(angle1),
            X12Gate(),
            RZ12Gate(angle2 - angle1),
            X12Gate(),
            RZ12Gate(-angle2),
        ]
