# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
#  OpenModes - An eigenmode solver for open electromagnetic resonantors
#  Copyright (C) 2013 David Powell
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------
"Fit scalar models to numerically calculated impedance data"

import numpy as np
from scipy.optimize import nnls


def fit_four_term(s_0, z_der):
    """
    Fit a 4 term model to a resonant frequency and impedance derivative
    To get reasonable condition number, omega_0 should be scaled to be near
    unity, and z_der should be scaled by the inverse of this factor
    """
    M = np.zeros((4, 4), np.float64)
    rhs = np.zeros(4, np.float64)
    
    # order of coefficients is C, R, L, R2
    
    # fit impedance being zero at resonance
    eq1 = np.array([1/s_0, 1, s_0, -s_0**2])
    M[0, :] = eq1.real
    M[1, :] = eq1.imag
    
    # fit impedance derivative at resonance
    eq2 = np.array([-1/s_0**2, 0, 1, -2*s_0])
    M[2, :] = eq2.real
    M[3, :] = eq2.imag
    
    rhs[2] = z_der.real
    rhs[3] = z_der.imag
    
    return nnls(M, rhs)[0]


class ScalarModel(object):
    """A scalar model of a mode of a structure, assuming that the eigencurrents
    are frequency independent. Fits a 4th order model to the eigenfrequency
    and the derivative of the eigenimpedancec at resonance, as well as the
    condition of open-circuit impedance at zero frequency."""
    
    def __init__(self, mode_s, mode_j, z_der):
        "Construct the scalar model"
        self.mode_s = mode_s
        self.mode_j = mode_j
        self.z_der = z_der
        self.coefficients = fit_four_term(mode_s/mode_s.imag, z_der*mode_s.imag)
    
    def scalar_impedance(self, s):
        "The scalar impedance of this mode"
        s = s/self.mode_s.imag
        powers = np.array([1/s, 1, s, -s**2])
        return np.dot(self.coefficients, powers.T)
    
    def solve(self, s, V):
        "Solve the model for the current at arbitrary frequency"
        return self.mode_j*np.dot(self.mode_j, V)/self.scalar_impedance(s)
