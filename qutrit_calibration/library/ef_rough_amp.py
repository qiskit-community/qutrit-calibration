# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
EF rough amplitude calibration experiment.
"""
from typing import Optional, List, Tuple

import numpy as np
from qiskit.circuit import QuantumCircuit, Gate, Parameter
from qiskit.providers import Backend
from qiskit.pulse import builder
from qiskit_experiments.calibration_management import BaseCalibrationExperiment
from qiskit_experiments.calibration_management.update_library import BaseUpdater
from qiskit_experiments.curve_analysis import OscillationAnalysis, ParameterRepr
from qiskit_experiments.framework import (
    BaseExperiment,
    ExperimentData,
    Options,
)

from qiskit_qutrit_calibration.framework import (
    QutritCalibrations,
    format_params,
    qutrit_context,
    play_calibration,
)


class RoughEFAmplitudeCal(BaseCalibrationExperiment, BaseExperiment):

    def __init__(
        self,
        physical_qubits: Tuple[int, ...],
        calibrations: QutritCalibrations,
        backend: Optional[Backend] = None,
    ):
        super().__init__(
            calibrations,
            physical_qubits,
            analysis=OscillationAnalysis(),
            backend=backend,
            auto_update=True,
        )
        self._setup()

    def _setup(self):
        self.analysis.set_options(
            normalization=False,
            result_parameters=[ParameterRepr("freq", "Ω12")],
        )
        self.analysis.plotter.set_figure_options(
            xlabel="Amplitude",
            ylabel="P(2)",
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            amp_min=-0.5,
            amp_max=0.5,
            amp_num=51,
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

    def circuits(self) -> List[QuantumCircuit]:
        opt = self.experiment_options
        amp_param = Parameter("amp")

        with builder.build() as rabi_sched:
            qutrit_context(self.calibrations, self.physical_qubits)
            play_calibration(
                calibrations=self.calibrations,
                name="x12",
                qubit=self.physical_qubits,
                amp=amp_param,
            )
        rabi_gate = Gate("rabi", num_qubits=1, params=[amp_param])

        tmp_circ = QuantumCircuit(1, 1)
        tmp_circ.x(0)
        tmp_circ.append(rabi_gate, [0])
        tmp_circ.x(0)
        tmp_circ.measure(0, 0)
        tmp_circ.add_calibration(rabi_gate, self.physical_qubits, rabi_sched)

        amps = np.linspace(opt.amp_min, opt.amp_max, opt.amp_num)
        circs = []
        for amp in amps:
            to_assign = format_params(amp)
            circ = tmp_circ.assign_parameters({amp_param: to_assign}, inplace=False)
            circ.metadata = {"xval": to_assign}
            circs.append(circ)

        return circs

    def update_calibrations(self, experiment_data: ExperimentData):
        rate = 2 * np.pi * BaseUpdater.get_value(experiment_data, "Ω12", -1)
        pi_amp = np.round(np.pi / rate, decimals=8)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=pi_amp,
            param="amp",
            schedule="x12",
        )
        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=pi_amp / 2,
            param="amp",
            schedule="sx12",
        )

    def _attach_calibrations(self, circuit: QuantumCircuit):
        pass
