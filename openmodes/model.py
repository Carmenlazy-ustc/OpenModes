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


def delta_eig(s, j, Z_func, eps = None):
    """Find the derivative of the eigenimpedance at the resonant frequency

    See section 5.7 of numerical recipes for calculating the step size h

    Impedance derivative is based on
    C. E. Baum, Proceedings of the IEEE 64, 1598 (1976).
    """

    if eps is None:
        # find the machine precision (this should actually be the accuracy with
        # which Z is calculated)
        eps = np.finfo(s.dtype).eps

    # first determine the optimal value of h
    h = abs(s)*eps**(1.0/3.0)*(1.0 + 1.0j)

    # make h exactly representable in floating point
    temp = s + h
    h = (temp - s)

    delta_Z = (Z_func(s+h)[:] - Z_func(s-h)[:])/(2*h)

    return np.dot(j.T, np.dot(delta_Z, j))


def fit_four_term(s_0, z_der, logger=None):
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
    
    if logger:
        logger.debug("Fitting 4 term polynomial\nM = %s\nrhs = %s" %
                    (str(M), str(rhs)))

    return nnls(M, rhs)[0]


class ScalarModel(object):
    """A scalar model of a mode of a structure, assuming that the eigencurrents
    are frequency independent. Fits a 4th order model to the eigenfrequency
    and the derivative of the eigenimpedancec at resonance, as well as the
    condition of open-circuit impedance at zero frequency."""

    def __init__(self, mode_s, mode_j, Z_func, logger=None):
        "Construct the scalar model"
        self.mode_s = mode_s
        self.mode_j = mode_j
        self.z_der = delta_eig(mode_s, mode_j, Z_func)
        self.scale_factor = abs(mode_s.imag)/10
        self.coefficients = fit_four_term(mode_s/self.scale_factor,
                                          self.z_der*self.scale_factor,
                                          logger)
        if logger:
            logger.info("Creating scalar model\ndlambda/ds = %+.4e %+.4e\n"
                        "Coefficients: %s" % (self.z_der.real, self.z_der.imag,
                                              str(self.coefficients)))

    def scalar_impedance(self, s):
        "The scalar impedance of this mode"
        s = s/self.scale_factor
        powers = np.array([1/s, 1, s, -s**2])
        return np.dot(self.coefficients, powers.T)

    def solve(self, s, V):
        "Solve the model for the current at arbitrary frequency"
        return self.mode_j*np.dot(self.mode_j, V)/self.scalar_impedance(s)

def fit_LS(s_0, L_0, S_0):
    """
    Fit a polynomial model to the values of the scalar impedance components
    at the resonant frequency. 
    
    Parameters
    ----------
    s_0 : complex
        The resonant frequency
    L : complex
        The scalar inductance at resonance
    S : complex
        The scalar susceptance at resonance

    Potentially extendable to include the second derivative (first derivative
    gives no extra information?)
    """

    M = np.zeros((2, 2))
    eq = np.array([1.0, -s_0])
    M[:, 0] = eq.real
    M[:, 1] = eq.imag

    L_coeffs = nnls(M, np.array([L_0.real, L_0.imag]))[0]

    eq = np.array([1.0, s_0])
    M[:, 0] = eq.real
    M[:, 1] = eq.imag
    
    S_coeffs = nnls(M, np.array([S_0.real, S_0.imag]))[0]

    return L_coeffs, S_coeffs

class ScalarModelLS(object):
    """A scalar model of a mode of a structure, assuming that the eigencurrents
    are frequency independent. Fits to the diagonalised partial impedance
    matrices L and S at resonance."""
    
    def __init__(self, mode_s, mode_j, Z_func, logger=None):
        "Construct the scalar model"
        self.mode_s = mode_s
        self.mode_j = mode_j
        Z = Z_func(mode_s)
        self.L_scale = 1e10
        self.S_scale = 1e-10
        L_0 = mode_j.dot(Z.L.dot(mode_j))
        S_0 = mode_j.dot(Z.S.dot(mode_j))
        self.scale_factor = abs(mode_s.imag)/10
        self.L, self.S = fit_LS(mode_s/self.scale_factor, L_0*self.L_scale, S_0*self.S_scale)

        if logger:
            logger.info("Creating scalar model\nL(s_0) = %+.4e %+.4e\n"
                        "S(s_0) = %+.4e %+.4e\nL Coefficients: %s\n"
                        "S Coefficients: %s" % 
                        (L_0.real, L_0.imag, S_0.real, S_0.imag,
                         str(self.L), str(self.S)))
    
    def scalar_impedance(self, s):
        "The scalar impedance of this mode"
        powers_L = np.array([1.0, -s/self.scale_factor])
        powers_S = np.array([1.0, s/self.scale_factor])
        return s*np.dot(self.L, powers_L.T)/self.L_scale + np.dot(self.S, powers_S.T)/s/self.S_scale
    
    def solve(self, s, V):
        "Solve the model for the current at arbitrary frequency"
        return self.mode_j*np.dot(self.mode_j, V)/self.scalar_impedance(s)
