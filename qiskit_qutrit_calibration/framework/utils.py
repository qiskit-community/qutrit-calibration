# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
Utilities.
"""

from typing import List, Sequence, Union, Optional
import decimal

from qiskit.circuit import QuantumCircuit, Gate
from qiskit.pulse import ControlChannel, SetFrequency
from qiskit.pulse.builder import _PulseBuilder, macro, set_frequency, call, delay, barrier
from qiskit.compiler import schedule

from qiskit_qutrit_calibration.framework import QutritCalibrations

decimal.getcontext().rounding = decimal.ROUND_DOWN


def format_params(value, digit=3):
    """Round assigned parameter value to avoid any float rounding issue."""

    round_val = round(decimal.Decimal(value), digit)
    return float(round_val)


def schedule_qutrit_circuit(
    circuit: QuantumCircuit,
    qubit_index: Union[int, Sequence[int]],
    calibrations: QutritCalibrations,
    meas_map: List[List[int]],
    is_v2: bool,
) -> QuantumCircuit:
    """Convert phase-sensitive qutrit circuit to a single pulse gate."""

    pulse_source = circuit.remove_final_measurements(inplace=False)

    if isinstance(qubit_index, int):
        qubit_index = (qubit_index, )
    qubit_index = tuple(qubit_index)

    pulse_gate = Gate("sequence", 1, [])
    circuit_schedule = schedule(
        pulse_source,
        inst_map=calibrations.default_inst_map,
        meas_map=meas_map,
    )
    anh = calibrations.get_parameter_value("α", qubit_index)
    f01 = calibrations.get_parameter_value("drive_freq", qubit_index)
    channel = calibrations.qutrit_channel(qubit_index)
    circuit_schedule.insert(
        0,
        SetFrequency(f01 + anh, channel),
        inplace=True,
    )
    if is_v2:
        payload = _PulseBuilder._naive_typecast_schedule(circuit_schedule)
    else:
        payload = circuit_schedule

    out = circuit.copy_empty_like()
    out.calibrations = {}
    out.append(pulse_gate, qubit_index)
    out.append(*circuit.get_instructions("measure"))
    out.add_calibration(pulse_gate, qubit_index, payload)

    return out


@macro
def qutrit_context(
    calibrations: QutritCalibrations,
    qubit: int,
    offset: float = 0.0,
) -> ControlChannel:
    channel = calibrations.qutrit_channel(qubit)
    anh = calibrations.get_parameter_value("α", qubit)
    f01 = calibrations.get_parameter_value("drive_freq", qubit)

    set_frequency(f01 + anh + offset, channel)

    return channel


@macro
def play_calibration(
    calibrations: QutritCalibrations,
    name: str,
    qubit: int,
    **override,
):
    subroutine = calibrations.get_schedule(
        name=name, qubits=qubit, assign_params=override
    )
    call(subroutine)
