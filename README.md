# Qutrit Calibration

[![License](https://img.shields.io/github/license/Qiskit/qiskit-experiments.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)

A qutrit experiment extension for [Qiskit Experiments](https://github.com/Qiskit/qiskit-experiments).  This package allows for straightforward calibration of single qutrit gates.

> **_Note:_** 
> 
> A word of caution: this package is an alpha release and subject to breaking API changes without much notice.

Once installed it can imported using

```python
import qiskit_qutrit_calibration
```

## Installation

This package can be in one of three ways:

1. Installed via pip as
```bash
pip install qiskit-qutrit-calibration
```

2. Installed from the downloaded repository using pip as

```bash
cd qiskit-qutrit-calibration
pip install .
```

3. Installed directly using the github url
```bash
pip install git+https://github.com/qiskit-community/qutrit-calibration
```

## Usage

This package allows users to spin up their own calibration experiments for single qutrit gates `SX12`, `X12`, `Sy12`, `Y12`, and `RZ12`.  The experiments to tune up these gates include:

- `RoughEFFrequencyCal`
- `RoughEFAmplitudeCal`
- `NarrowBandSpectroscopyCal`
- `RoughEFXDragCal`
- `FineEFXAmplitudeCal`

Simply create a new `QutritCalibrations` object using 
```python
cals = QutritCalibrations.from_backend(backend)
```
Then execute an experiment using the instantiated `QutritCalibrations`, a `Tuple` of qubit indices, and backend to run on.  For example,

```python
from qiskit_qutrit_calibration import library

exp = library.RoughEFFrequencyCal( (qubit_index), calibrations=cals, backend=backend )
```


## License

[Apache License 2.0](LICENSE.txt)
