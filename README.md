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

## Development Scripts

This package includes several pre-configured `tox` scripts for automating
development of your package. These commands can be run from the command line

```bash
cd qutrit-calibration
tox -e <command>
```

| Command | Description |
| ------- | ----------- |
| ``py` | Run unit tests for the package using [stestr](https://github.com/mtreinish/stestr)|
| ``black`` | Auto-format your package files using [Black](https://github.com/psf/black) |
| ``lint`` | Run PyLint on your package to check code formatting. Note that linting will fail if running ``black`` would modify any files |
| ``docs`` | Generate documentation for the package using Sphinx |

If you do not already have the tox command installed, install it by running

```bash
pip install tox
```

## Testing Your Package

This package is configured with `stestr` and `tox` scripts to run unit tests
added to the ``qutrit-calibration/test`` folder.

These can be run directly via ``stestr`` using the command

```bash
cd qutrit-calibration
stestr run
```

Or using to tox script ``tox -e py`` to install all dependencies and run the tests
in an isolated virtual environment.

To add tests to your package you must including them in a files prefixed as
`test_*.py` in the `test/` folder or a subfolder. Tests should be written
using the ``unittest`` framework to make a test class containing each test
as a separate method prefixed as `test_*`.

For example:

```python

class BasicTests(unittest.TestCase):
    """Some basic tests for Qiskit Qutrit Calibration"""

    def test_something(self):
        """A basic test of something"""
        # Write some code here
        some_value = ...
        target = ...
        self.assertTrue(some_value, target)
```

## Documenting Your Package

You can add documentation or tutorials to your package by including it in the
``qutrit-calibration/docs`` folder and building it locally using
the ``tox -edocs`` command.

Documentation is build using Sphinx. By default will include any API documentation
added to your packages main ``__init__.py`` file.

## License

[Apache License 2.0](LICENSE.txt)
