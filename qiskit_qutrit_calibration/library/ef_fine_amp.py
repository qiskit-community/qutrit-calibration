# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
EF fine amplitude calibration experiment.
"""
from abc import abstractmethod
from typing import Optional, List, Tuple

import numpy as np
from qiskit.circuit import QuantumCircuit, Gate
from qiskit.providers import Backend
from qiskit.pulse import builder
from qiskit_experiments.calibration_management import BaseCalibrationExperiment
from qiskit_experiments.calibration_management.update_library import BaseUpdater
from qiskit_experiments.curve_analysis import ParameterRepr
from qiskit_experiments.framework import (
    BaseExperiment,
    ExperimentData,
    Options,
)
from qiskit_experiments.library.characterization.analysis import FineAmplitudeAnalysis
from qiskit_qutrit_calibration.framework import (
    QutritCalibrations,
    qutrit_context,
    play_calibration,
)


class FineEFAmplitudeCal(BaseCalibrationExperiment, BaseExperiment):

    def __init__(
        self,
        physical_qubits: Tuple[int, ...],
        calibrations: QutritCalibrations,
        backend: Optional[Backend] = None,
    ):
        super().__init__(
            calibrations,
            physical_qubits,
            analysis=FineAmplitudeAnalysis(),
            backend=backend,
            auto_update=True,
        )
        self._setup()

    def _setup(self):
        self.analysis.set_options(
            normalization=False,
            result_parameters=[ParameterRepr("d_theta", "d_theta12")],
        )
        self.analysis.plotter.set_figure_options(
            xlabel="Drive amplitude",
            ylabel="P(2)",
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(nreps=None)
        return options

    @classmethod
    def _default_run_options(cls) -> Options:
        """Default options values for the experiment :meth:`run` method."""
        options = Options()
        options.use_measure_esp = False
        options.shots = 1024
        options.rep_delay = 300e-6

        return options

    @abstractmethod
    def _sequence_under_test(self, nrep: int) -> QuantumCircuit:
        pass

    def circuits(self) -> List[QuantumCircuit]:
        opt = self.experiment_options

        # Prepare SPAM cal circuit.
        # Since this is SPAM cal, measuring 0/1 state is sufficient because
        # we use x-measure sequence with default hardware discriminator.
        circ0 = QuantumCircuit(1, 1)
        circ0.id(0)
        circ0.measure(0, 0)
        circ0.metadata = {
            "xval": 0,
            "series": "spam-cal",
        }

        circ1 = QuantumCircuit(1, 1)
        circ1.x(0)
        circ1.measure(0, 0)
        circ1.metadata = {
            "xval": 1,
            "series": "spam-cal",
        }

        circs = [circ0, circ1]
        for nrep in opt.nreps:
            circ = QuantumCircuit(1, 1)
            circ.x(0)
            circ.compose(self._sequence_under_test(nrep), inplace=True)
            circ.x(0)
            circ.measure(0, 0)
            circ.metadata = {
                "xval": nrep,
                "series": 1,
            }
            circs.append(circ)

        return circs

    def _attach_calibrations(self, circuit: QuantumCircuit):
        pass


class FineEFSXAmplitudeCal(FineEFAmplitudeCal):

    def _setup(self):
        super()._setup()
        self.set_experiment_options(
            nreps=[1, 3, 5, 7, 9, 11, 13, 15, 17, 21, 23, 25],
        )
        self.analysis.set_options(
            fixed_parameters={
                "angle_per_gate": np.pi / 2,
                "phase_offset": np.pi,
            }
        )

    def _sequence_under_test(self, nrep: int) -> QuantumCircuit:
        sequence = Gate(f"amplification_{nrep:02d}", 1, [])

        # repeated gate is phase sensitive
        qc_test = QuantumCircuit(1)
        qc_test.append(sequence, [0])

        with builder.build() as sequence_sched:
            qutrit_context(self.calibrations, self.physical_qubits)
            for _ in range(nrep):
                play_calibration(
                    calibrations=self.calibrations,
                    name="sx12",
                    qubit=self.physical_qubits,
                )
        qc_test.add_calibration(sequence, self.physical_qubits, sequence_sched)

        return qc_test

    def update_calibrations(self, experiment_data: ExperimentData):

        current_amp = self.calibrations.get_parameter_value(
            param="amp",
            qubits=self.physical_qubits,
            schedule="sx12",
        )

        angle_error = BaseUpdater.get_value(experiment_data, "d_theta12", -1)
        target_anle = np.pi / 2
        new_amp = current_amp * target_anle / (target_anle + angle_error)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=new_amp,
            param="amp",
            schedule="sx12",
        )


class FineEFXAmplitudeCal(FineEFAmplitudeCal):

    def _setup(self):
        super()._setup()
        self.set_experiment_options(
            nreps=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        )
        self.analysis.set_options(
            fixed_parameters={
                "angle_per_gate": np.pi,
                "phase_offset": np.pi / 2,
            }
        )

    def _sequence_under_test(self, nrep: int) -> QuantumCircuit:
        sequence = Gate(f"amplification_{nrep:02d}", 1, [])

        # repeated gate is phase sensitive
        qc_test = QuantumCircuit(1)
        qc_test.append(sequence, [0])

        with builder.build() as sequence_sched:
            qutrit_context(self.calibrations, self.physical_qubits)
            play_calibration(
                calibrations=self.calibrations,
                name="sx12",
                qubit=self.physical_qubits,
            )
            for _ in range(nrep):
                play_calibration(
                    calibrations=self.calibrations,
                    name="x12",
                    qubit=self.physical_qubits,
                )
        qc_test.add_calibration(sequence, self.physical_qubits, sequence_sched)

        return qc_test

    def update_calibrations(self, experiment_data: ExperimentData):

        current_amp = self.calibrations.get_parameter_value(
            param="amp",
            qubits=self.physical_qubits,
            schedule="x12",
        )

        angle_error = BaseUpdater.get_value(experiment_data, "d_theta12", -1)
        target_anle = np.pi
        new_amp = current_amp * target_anle / (target_anle + angle_error)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=new_amp,
            param="amp",
            schedule="x12",
        )
