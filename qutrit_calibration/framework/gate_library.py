# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
Qutrit gate template.
"""

from typing import Dict, Set, List, Optional

import numpy as np

from qiskit.circuit import Parameter
from qiskit.pulse import builder, library, channels, ScheduleBlock
from qiskit_experiments.calibration_management import BasisGateLibrary
from qiskit_experiments.calibration_management.calibration_key_types import DefaultCalValue


class SingleQutrit(BasisGateLibrary):
    """Single qutrit gates in e-f subspace."""

    __default_values__ = {
        "duration": 160,
        "amp": 0.14,
        "angle": 0.0,
        "σ": 40,
        "β": 0.0,
        "α": -300e6,
    }

    def __init__(
        self,
        basis_gates: Optional[List[str]] = None,
        default_values: Optional[Dict] = None,
    ):
        super().__init__(basis_gates, default_values)

    @property
    def __supported_gates__(self) -> Dict[str, int]:
        return {"x12": 1, "y12": 1, "sx12": 1, "sy12": 1}

    def _build_schedules(self, basis_gates: Set[str]) -> Dict[str, ScheduleBlock]:
        dur = Parameter("duration")
        sigma = Parameter("σ")
        ch_ind = Parameter("ch0$0")

        hp_amp, hp_beta, hp_angle = Parameter("amp"), Parameter("β"), Parameter("angle")
        pi_amp, pi_beta, pi_angle = Parameter("amp"), Parameter("β"), Parameter("angle")

        channel = channels.ControlChannel(ch_ind)

        with builder.build(name="x12") as x_sched:
            builder.play(
                library.Drag(
                    duration=dur,
                    amp=pi_amp,
                    sigma=sigma,
                    beta=pi_beta,
                    angle=pi_angle,
                ),
                channel,
            )

        with builder.build(name="y12") as y_sched:
            builder.play(
                library.Drag(
                    duration=dur,
                    amp=pi_amp,
                    sigma=sigma,
                    beta=pi_beta,
                    angle=pi_angle + np.pi / 2,
                ),
                channel,
            )

        with builder.build(name="sx12") as sx_sched:
            builder.play(
                library.Drag(
                    duration=dur,
                    amp=hp_amp,
                    sigma=sigma,
                    beta=hp_beta,
                    angle=hp_angle,
                ),
                channel,
            )

        with builder.build(name="sy12") as sy_sched:
            builder.play(
                library.Drag(
                    duration=dur,
                    amp=hp_amp,
                    sigma=sigma,
                    beta=hp_beta,
                    angle=hp_angle + np.pi / 2,
                ),
                channel,
            )

        schedules = {}
        for sched in [sx_sched, sy_sched, x_sched, y_sched]:
            if sched.name in basis_gates:
                schedules[sched.name] = sched

        return schedules

    def default_values(self) -> List[DefaultCalValue]:
        defaults = [
            DefaultCalValue(self._default_values["duration"], "duration", tuple(), "x12"),
            DefaultCalValue(self._default_values["amp"], "amp", tuple(), "x12"),
            DefaultCalValue(self._default_values["σ"], "σ", tuple(), "x12"),
            DefaultCalValue(self._default_values["β"], "β", tuple(), "x12"),
            DefaultCalValue(self._default_values["angle"], "angle", tuple(), "x12"),
            DefaultCalValue(0.5 * self._default_values["amp"], "amp", tuple(), "sx12"),
            DefaultCalValue(self._default_values["β"], "β", tuple(), "sx12"),
            DefaultCalValue(self._default_values["angle"], "angle", tuple(), "sx12"),
            DefaultCalValue(self._default_values["α"], "α", tuple(), None),
        ]

        return defaults
