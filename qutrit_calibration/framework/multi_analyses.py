# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
A composite curve analysis class that runs multiple analyses on the same data.
"""

import warnings

from typing import List, Tuple
from qiskit_experiments.framework import BaseAnalysis, ExperimentData, AnalysisResultData
from qiskit_experiments.curve_analysis.base_curve_analysis import PARAMS_ENTRY_PREFIX

import numpy as np


class MultipleCurveAnalysis(BaseAnalysis):
    """Run different analyses on the same data and return best analysis results."""

    def __init__(self, *analyses):
        super().__init__()
        self.analyses = analyses

    def _run_analysis(
        self,
        experiment_data: ExperimentData,
    ) -> Tuple[List[AnalysisResultData], List["matplotlib.figure.Figure"]]:

        all_results = []
        all_figures = []
        chisqs = []
        for analysis in self.analyses:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    results, figures = analysis._run_analysis(experiment_data)
            except Exception:
                continue
            for res in results:
                if res.name.startswith(PARAMS_ENTRY_PREFIX):
                    try:
                        chisq = res.value.chisq
                    except AttributeError:
                        chisq = np.nan
                    break
            else:
                continue
            all_results.append(results)
            all_figures.append(figures)
            chisqs.append(chisq)

        if not chisqs:
            return [], []

        best_analysis_index = np.nanargmin(chisqs)
        return all_results[best_analysis_index], all_figures[best_analysis_index]
