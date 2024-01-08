# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
EF spectroscopy calibration experiment.
"""
import warnings
from abc import abstractmethod
from typing import Optional, List, Tuple, Union

import lmfit
import numpy as np
import qiskit_experiments.curve_analysis as curve

from scipy.signal import find_peaks

from qiskit.circuit import QuantumCircuit, Gate, Parameter
from qiskit.providers import Backend
from qiskit.pulse import builder, library
from qiskit_experiments.calibration_management import BaseCalibrationExperiment
from qiskit_experiments.calibration_management.update_library import BaseUpdater
from qiskit_experiments.framework import (
    BaseExperiment,
    ExperimentData,
    BackendTiming,
    Options,
)
from qiskit_experiments.database_service.exceptions import ExperimentEntryNotFound
from qiskit_qutrit_calibration.framework import (
    MultipleCurveAnalysis,
    QutritCalibrations,
    format_params,
    qutrit_context,
)


class SinglePeakResonanceAnalysis(curve.ResonanceAnalysis):
    @classmethod
    def _default_options(cls) -> Options:
        options = super()._default_options()
        options.plotter.set_figure_options(
            xlabel="Detuning",
            ylabel="P(2)",
            xval_unit="Hz",
        )
        options.result_parameters = [curve.ParameterRepr("freq", "Δα", "Hz")]
        options.normalization = False
        return options

    def _generate_fit_guesses(
        self,
        user_opt: curve.FitOptions,
        curve_data: curve.CurveData,
    ) -> Union[curve.FitOptions, List[curve.FitOptions]]:
        # Enforce positive peak, because this is level2 measurement
        max_abs_y, _ = curve.guess.max_height(curve_data.y)

        user_opt.bounds.set_if_empty(
            a=(0, 2 * max_abs_y),
            kappa=(0, np.ptp(curve_data.x)),
            freq=(min(curve_data.x), max(curve_data.x)),
            b=(0, max_abs_y),
        )
        user_opt.p0.set_if_empty(b=curve.guess.constant_spectral_offset(curve_data.y))

        y_ = curve_data.y - user_opt.p0["b"]

        _, peak_idx = curve.guess.max_height(y_)
        fwhm = curve.guess.full_width_half_max(curve_data.x, y_, peak_idx)

        user_opt.p0.set_if_empty(
            a=(curve_data.y[peak_idx] - user_opt.p0["b"]),
            freq=curve_data.x[peak_idx],
            kappa=fwhm,
        )

        return user_opt


class DoublePeakResonanceAnalysis(curve.CurveAnalysis):
    """Lorentzian fit with two peaks."""

    def __init__(self):
        temp = "a[i] * abs(kappa[i]) / sqrt(kappa[i]**2 + 4 * (x - x[i])**2)"
        model = ""
        for ind in range(2):
            model += temp.replace("[i]", str(ind))
            model += " + "
        model += "offset"

        super().__init__(
            models=[
                lmfit.models.ExpressionModel(
                    expr=model,
                    name="double_lorentzian",
                )
            ],
            name="double_lorentzian",
        )

    @classmethod
    def _default_options(cls) -> Options:
        options = super()._default_options()
        options.plotter.set_figure_options(
            xlabel="Detuning",
            ylabel="P(2)",
            xval_unit="Hz",
        )
        options.result_parameters = [
            curve.ParameterRepr("x0", "Δα0", "Hz"),
            curve.ParameterRepr("x1", "Δα1", "Hz"),
        ]
        options.normalization = False
        return options

    def _generate_fit_guesses(
        self,
        user_opt: curve.FitOptions,
        curve_data: curve.CurveData,
    ) -> Union[curve.FitOptions, List[curve.FitOptions]]:
        max_abs_y, _ = curve.guess.max_height(curve_data.y, absolute=True)

        user_opt.bounds.set_if_empty(
            a0=(-2 * max_abs_y, 2 * max_abs_y),
            a1=(-2 * max_abs_y, 2 * max_abs_y),
            kappa0=(0, np.ptp(curve_data.x)),
            kappa1=(0, np.ptp(curve_data.x)),
            x0=(min(curve_data.x), max(curve_data.x)),
            x1=(min(curve_data.x), max(curve_data.x)),
            offset=(-max_abs_y, max_abs_y),
        )
        user_opt.p0.set_if_empty(
            offset=curve.guess.constant_spectral_offset(curve_data.y)
        )

        peaks, properties = find_peaks(
            curve_data.y,
            height=(0.5 * max_abs_y, 1.0),
            width=(3, None),
        )
        hights = properties["peak_heights"]
        widths = properties["widths"]

        if len(peaks) < 2:
            warnings.warn(
                "Two peaks are not found. Use lower resolution or wider detuning range.",
                UserWarning,
            )
            return user_opt

        from_higher = np.argsort(hights)[::-1]
        opt = {}
        for peak_ind in range(2):
            ind = from_higher[peak_ind]
            opt[f"a{ind}"] = hights[ind] - user_opt.p0["offset"]
            opt[f"kappa{ind}"] = widths[ind]
            opt[f"x{ind}"] = curve_data.x[peaks[ind]]
        user_opt.p0.set_if_empty(**opt)

        return user_opt


class EFFrequencyCal(BaseCalibrationExperiment, BaseExperiment):

    def __init__(
        self,
        physical_qubits: Tuple[int, ...],
        calibrations: QutritCalibrations,
        backend: Optional[Backend] = None,
    ):
        super().__init__(
            calibrations,
            physical_qubits,
            backend=backend,
            auto_update=True,
        )
        self._setup()

    def _setup(self):
        pass

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            detuning_min=-20e6,
            detuning_max=20e6,
            detuning_num=101,
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
    def _spect_schedule(self, detuning_param: Parameter):
        pass

    def circuits(self) -> List[QuantumCircuit]:
        opt = self.experiment_options

        detuning_param = Parameter("detuning")

        spect_sched = self._spect_schedule(detuning_param)
        spect_gate = Gate("spect", num_qubits=1, params=[detuning_param])

        tmp_circ = QuantumCircuit(1, 1)
        tmp_circ.x(0)
        tmp_circ.append(spect_gate, [0])
        tmp_circ.x(0)
        tmp_circ.measure(0, 0)
        tmp_circ.add_calibration(spect_gate, self.physical_qubits, spect_sched)

        detunings = np.linspace(opt.detuning_min, opt.detuning_max, opt.detuning_num)
        circs = []
        for detuning in detunings:
            to_assign = format_params(detuning)
            circ = tmp_circ.assign_parameters({detuning_param: to_assign}, inplace=False)
            circ.metadata = {"xval": to_assign}
            circs.append(circ)

        return circs

    def _attach_calibrations(self, circuit: QuantumCircuit):
        pass


class RoughEFFrequencyCal(EFFrequencyCal):

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            duration=1120,
            sigma=280,
            amp=0.01,
        )

        return options

    def _setup(self):
        self.analysis = SinglePeakResonanceAnalysis()

    def _spect_schedule(self, detuning_param: Parameter):
        opt = self.experiment_options
        timing = BackendTiming(self.backend)

        with builder.build() as spect_sched:
            channel = qutrit_context(self.calibrations, self.physical_qubits, detuning_param)
            builder.play(
                library.Gaussian(
                    duration=timing.round_pulse(samples=opt.duration),
                    amp=opt.amp,
                    sigma=opt.sigma,
                ),
                channel=channel,
            )

        return spect_sched

    def update_calibrations(self, experiment_data: ExperimentData):
        delta = BaseUpdater.get_value(experiment_data, "Δα", -1)
        anh = self.calibrations.get_parameter_value("α", self.physical_qubits)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=anh + delta,
            param="α",
        )


class NarrowBandEFSpectroscopyCal(EFFrequencyCal):

    @classmethod
    def _default_experiment_options(cls) -> Options:
        options = super()._default_experiment_options()
        options.update_options(
            detuning_min=-3e6,
            detuning_max=3e6,
            detuning_num=150,
            resolution=1e6,
        )

        return options

    def _setup(self):
        # When amplitude is high or charge noise is stable,
        # it could be difficult to find charge splitting.
        # Then, it falls into single peak fitting.
        self.analysis = MultipleCurveAnalysis(
            DoublePeakResonanceAnalysis(),
            SinglePeakResonanceAnalysis(),
        )

    def _spect_schedule(self, detuning_param: Parameter):
        opt = self.experiment_options
        timing = BackendTiming(self.backend)

        # Compute amplitude and sigma of very weak spectroscopy pulse
        ref_amp = self.calibrations.get_parameter_value("amp", self.physical_qubits, "x12")
        ref_sigma = self.calibrations.get_parameter_value("σ", self.physical_qubits, "x12")
        pi_area = ref_amp * ref_sigma * np.sqrt(2 * np.pi)

        # Compute gaussian amplitude to keep the same area under curve
        # duration is assumed to be 4 sigma
        duration = timing.round_pulse(time=4 / opt.resolution)
        sigma = duration / 4
        amp = pi_area / (sigma * np.sqrt(2 * np.pi))

        with builder.build() as spect_sched:
            channel = qutrit_context(self.calibrations, self.physical_qubits, detuning_param)
            builder.play(
                library.Gaussian(
                    duration=duration,
                    amp=amp,
                    sigma=sigma,
                ),
                channel=channel,
            )

        return spect_sched

    def update_calibrations(self, experiment_data: ExperimentData):
        try:
            delta_0 = BaseUpdater.get_value(experiment_data, "Δα0", -1)
            delta_1 = BaseUpdater.get_value(experiment_data, "Δα1", -1)
            delta = 0.5 * (delta_0 + delta_1)
        except ExperimentEntryNotFound:
            delta = BaseUpdater.get_value(experiment_data, "Δα", -1)
        anh = self.calibrations.get_parameter_value("α", self.physical_qubits)

        BaseUpdater.add_parameter_value(
            cal=self.calibrations,
            exp_data=experiment_data,
            value=anh + delta,
            param="α",
        )
