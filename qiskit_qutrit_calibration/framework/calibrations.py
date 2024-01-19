# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
Qutrit Calibrations.
"""

import warnings
from typing import List, Optional

import numpy as np
from qiskit.circuit import Parameter
from qiskit.providers import Backend
from qiskit.pulse import channels, Schedule, ShiftPhase
from qiskit_experiments.calibration_management import (
    Calibrations,
    ParameterValue,
    BasisGateLibrary,
)
from qiskit_experiments.framework import BackendData


class QutritCalibrations(Calibrations):
    """Qutrit calibration."""

    @classmethod
    def from_backend(
        cls,
        backend: Backend,
        libraries: Optional[List[BasisGateLibrary]] = None,
        add_parameter_defaults: bool = True,
    ) -> "QutritCalibrations":
        """This method modify backend architecture for qutrit.

        Because qutrit experiment uses schedule payload, all single qubit gates
        are ported from the backend instruction schedule map to calibrations.

        * Remove control channels from backend provided schedule.
        * Ignore instructions taking more than one qubit.
        * Use control channel for qutrit control -- modify control channel map.
        """
        backend_data = BackendData(backend)

        cmap = np.asarray(backend_data.coupling_map, dtype=int)

        control_channel_map = {}
        blacklist = []
        for qubit in range(backend_data.num_qubits):
            # find control channel controlling the qubit.
            # assume all CRs are disabled.
            # all control channels are now for qutrit control
            available_cmap = cmap[np.nonzero(cmap[:, 0] == qubit)]
            try:
                channel = backend_data.control_channel(tuple(available_cmap[0]))[0]
            except IndexError:
                warnings.warn(
                    f"ControlChannel for qubit{qubit} does not exist. This qubit cannot be used."
                )
                blacklist.append(qubit)
                continue
            control_channel_map[(qubit,)] = [channel]

        cals = QutritCalibrations(
            coupling_map=[[qubit] for qubit in range(backend_data.num_qubits)],
            control_channel_map=control_channel_map,
            libraries=libraries,
            add_parameter_defaults=add_parameter_defaults,
            backend_name=backend_data.name,
            backend_version=backend_data.version,
        )
        cals.blacklist = blacklist

        # Add extra global parameter for anharmonicity
        for qubit in range(backend_data.num_qubits):
            sideband = Parameter("α")
            cals._register_parameter(sideband, (qubit, ))

        if add_parameter_defaults:
            for qubit, freq in enumerate(backend_data.drive_freqs):
                cals.add_parameter_value(freq, cals.drive_freq, qubit, update_inst_map=False)

            for meas, freq in enumerate(backend_data.meas_freqs):
                cals.add_parameter_value(freq, cals.meas_freq, meas, update_inst_map=False)

            # Add default anharmonicity value. not supported by V2
            for qubit in range(backend_data.num_qubits):
                anhval, datetime = backend.properties().qubit_property(qubit, "anharmonicity")
                to_add = ParameterValue(value=anhval, date_time=datetime, valid=True)
                cals.add_parameter_value(
                    value=to_add,
                    param="α",
                    qubits=(qubit,),
                    update_inst_map=False,
                )

        # Update the instruction schedule map after adding all parameter values.
        cals.update_inst_map()
        cals.complete_inst_map(backend)

        return cals

    def complete_inst_map(
        self,
        backend: Backend,
        gates_to_add: List[str] = ("x", "sx", "rz", "rz12"),
    ):
        """Add missing entries for circuit scheduling to inst map."""
        backend_data = BackendData(backend)

        # Add backend cals by excluding default control channels.
        backend_inst_map = backend.defaults().instruction_schedule_map
        for qubit in range(backend_data.num_qubits):
            for gate in gates_to_add:
                if not backend_inst_map.has(gate, (qubit, )):
                    continue
                temp_schedule = backend_inst_map.get(gate, (qubit, ))
                sched_insts = []
                for t0, inst in temp_schedule.instructions:
                    if any(isinstance(chan, channels.ControlChannel) for chan in inst.channels):
                        continue
                    sched_insts.append((t0, inst))
                schedule = Schedule(*sched_insts, name=gate)
                self._inst_map.add(
                    instruction=gate,
                    qubits=(qubit, ),
                    schedule=schedule,
                )

        if "rz12" in gates_to_add:
            for qubit in range(backend_data.num_qubits):
                qutrit_chan = self._control_channel_map[(qubit, )][0]
                rz_schedule = Schedule(name="rz12")
                rz_schedule.insert(0, ShiftPhase(-Parameter("θ"), qutrit_chan), inplace=True)
                self._inst_map.add("rz12", (qubit, ), rz_schedule)

    def qutrit_channel(self, index):
        """Return qutrit drive channel."""
        if isinstance(index, int):
            index = (index, )
        return self._control_channel_map[tuple(index)][0]

    @classmethod
    def load(cls, file_path: str) -> "QutritCalibrations":
        instance = super().load(file_path)
        instance.__class__ = QutritCalibrations

        return instance
