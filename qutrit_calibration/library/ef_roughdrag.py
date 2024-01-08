# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
EF rough DRAG calibration experiment.
"""
from abc import abstractmethod
from typing import Optional, List, Tuple

import numpy as np
from qiskit.circuit import QuantumCircuit, Gate, Parameter
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
from qiskit_experiments.library.characterization.analysis import DragCalAnalysis

from qiskit_qutrit_calibration.framework import (
    QutritCalibrations,
    format_params,
    qutrit_context,
    play_calibration,
)


class RoughEFDragCal(BaseCalibrationExperiment, BaseExperiment):

    def __init__(
        self,
        physical_qubits: Tuple[int, ...],
        calibrations: QutritCalibrations,
        backend: Optional[Backend] = None,
    ):
        super().__init__(
            calibrations,
            physical_qubits,
            analysis=DragCalAnalysis(),
            backend=backend,
        )
        self._setup()

    def _setup(self):
        self.analysis.set_options(
            normalization=False,
            result_parameters=[ParameterRepr("beta", "β12")],
        )
        self.analysis.plotter.set_figure_options(
            xlabel="β",
            ylabel="P(2)",
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            beta_min=-5,
            beta_max=5,
            beta_num=51,
            reps=[1, 3, 5],
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

    @abstractmethod
    def _sequence_under_test(self, nrep: int, beta_param: Parameter) -> QuantumCircuit:
        pass

    def circuits(self) -> List[QuantumCircuit]:
        opt = self.experiment_options
        beta_param = Parameter("beta")

        circs = []
        for nrep in opt.reps:
            tmp_circ = QuantumCircuit(1, 1)
            tmp_circ.x(0)
            tmp_circ.compose(self._sequence_under_test(nrep, beta_param), inplace=True)
            tmp_circ.x(0)
            tmp_circ.measure(0, 0)

            betas = np.linspace(opt.beta_min, opt.beta_max, opt.beta_num)
            for beta in betas:
                to_assign = format_params(beta)
                circ = tmp_circ.assign_parameters({beta_param: to_assign}, inplace=False)
                circ.metadata = {"xval": to_assign, "nrep": nrep}
                circs.append(circ)

        return circs

    def _finalize(self):
        self.analysis.set_options(reps=self.experiment_options.reps)

    def _attach_calibrations(self, circuit: QuantumCircuit):
        pass


class RoughEFXDragCal(RoughEFDragCal):

    def _sequence_under_test(self, nrep: int, beta_param: Parameter) -> QuantumCircuit:
        sequence = Gate(f"amplification_{nrep:02d}", 1, [beta_param])

        # repeated gate is phase sensitive
        qc_test = QuantumCircuit(1)
        qc_test.append(sequence, [0])

        with builder.build() as sequence_sched:
            qutrit_context(self.calibrations, self.physical_qubits)
            for _ in range(nrep):
                play_calibration(
                    calibrations=self.calibrations,
                    name="x12",
                    qubit=self.physical_qubits,
                    β=beta_param,
                    angle=0.0,
                )
                play_calibration(
                    calibrations=self.calibrations,
                    name="x12",
                    qubit=self.physical_qubits,
                    β=beta_param,
                    angle=np.pi,
                )
        qc_test.add_calibration(sequence, self.physical_qubits, sequence_sched)

        return qc_test

    def update_calibrations(self, experiment_data: ExperimentData):
        beta = BaseUpdater.get_value(experiment_data, "β12", -1)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=beta,
            param="β",
            schedule="x12",
        )


class RoughEFSXDragCal(RoughEFDragCal):

    def _sequence_under_test(self, nrep: int, beta_param: Parameter) -> QuantumCircuit:
        sequence = Gate(f"amplification_{nrep:02d}", 1, [beta_param])

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
                    β=beta_param,
                    angle=0.0,
                )
                play_calibration(
                    calibrations=self.calibrations,
                    name="sx12",
                    qubit=self.physical_qubits,
                    β=beta_param,
                    angle=np.pi,
                )
        qc_test.add_calibration(sequence, self.physical_qubits, sequence_sched)

        return qc_test

    def update_calibrations(self, experiment_data: ExperimentData):
        beta = BaseUpdater.get_value(experiment_data, "β12", -1)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=beta,
            param="β",
            schedule="sx12",
        )
