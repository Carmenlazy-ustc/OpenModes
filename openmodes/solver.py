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


from __future__ import division#, print_function

# numpy and scipy
import numpy as np
#import scipy.linalg as la
#import itertools
from scipy.optimize import nnls

#from openmodes.constants import epsilon_0, mu_0    
#from openmodes.utils import SingularSparse
from openmodes import integration
from openmodes.parts import Part#, Triangles, RwgBasis

from openmodes.impedance import ImpedanceParts
from openmodes.basis import LoopStarBasis, get_basis_functions
from openmodes.operator import EfieOperator, FreeSpaceGreensFunction
from openmodes.eig import eig_linearised, eig_newton
from openmodes.visualise import plot_mayavi, write_vtk
from openmodes.model import ScalarModel


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

    delta_Z = (Z_func(s+h) - Z_func(s-h))/(2*h)
    
    return np.dot(j.T, np.dot(delta_Z, j))


class Simulation(object):
    """This object controls everything within the simluation. It contains all
    the parts which have been placed, and the operator equation which is
    used to solve the scattering problem.
    """

    def __init__(self, integration_rule = 5, basis_class = LoopStarBasis,
                 operator_class = EfieOperator, 
                 greens_function=FreeSpaceGreensFunction()):
        """       
        Parameters
        ----------
        integration_rule : integer
            the order of the integration rule on triangles
        """

        self.quadrature_rule = integration.get_dunavant_rule(integration_rule)

        self.triangle_quadrature = {}
        self.singular_integrals = {}

        self.parts = []

        self.basis_class = basis_class
        self.operator = operator_class(quadrature_rule=self.quadrature_rule,
                                       basis_class=basis_class, 
                                       greens_function=greens_function)

    def place_part(self, mesh, location=None):
        """Add a part to the simulation domain
        
        Parameters
        ----------
        mesh : an appropriate mesh object
            The part to place
        location : array, optional
            If specified, place the part at a given location, otherwise it will
            be placed at the origin
            
        Returns
        -------
        part : Part
            The part placed in the simulation
            
        The part will be placed at the origin. It can be translated, rotated
        etc using the relevant methods of `Part`            
        """
        
        sim_part = Part(mesh, location=location) 
        self.parts.append(sim_part)

        return sim_part

    def calculate_impedance(self, s):
        """Evaluate the self and mutual impedances of all parts in the
        simulation. Return an `ImpedancePart` object which can calculate
        several derived impedance quantities

        Parameters
        ----------        
        s : number
            complex frequency at which to calculate impedance (in rad/s)

        Returns
        -------
        impedance_matrices : ImpedanceParts
            The impedance matrix object which can represent the impedance of
            the object in several ways.
        """

        matrices = []

        # TODO: cache individual part impedances to avoid repetition?
        # May not be worth it because mutual impedances cannot be cached
        # except in specific cases such as arrays

        for index_a, part_a in enumerate(self.parts):
            matrices.append([])
            for index_b, part_b in enumerate(self.parts):
                if (index_b < index_a) and self.operator.reciprocal:
                    # use reciprocity to avoid repeated calculation
                    res = matrices[index_b][index_a].T
                else:
                    res = self.operator.impedance_matrix(s, part_a, part_b)
                matrices[-1].append(res)

        return ImpedanceParts(s, len(self.parts), matrices)

    def source_plane_wave(self, e_inc, jk_inc):
        """Evaluate the source vectors due to an incident plane wave, returning
        separate vectors for each part.

        Parameters
        ----------        
        e_inc: ndarray
            incident field polarisation in free space
        jk_inc: ndarray
            incident wave vector in free space

        Returns
        -------
        V : list of ndarray
            the source vector for each part
        """
        return [self.operator.source_plane_wave(part, e_inc, jk_inc) for part 
                in self.parts]

    def part_singularities(self, s_start, num_modes):
        """Find the singularities of the system in the complex frequency plane

        Parameters
        ----------        
        s_start : number
            The complex frequency at which to perform the estimate. Should be
            within the band of interest
        """

        all_s = []
        all_j = []   

        solved_parts = {}

        for part in self.parts:
            # TODO: unique ID needs to be modified if different materials or
            # placement above a layer are possible

            unique_id = (part.mesh.id,) # cache identical parts 
            if unique_id in solved_parts:
                #print "got from cache"
                mode_s, mode_j = solved_parts[unique_id]
            else:
                # first get an estimate of the pole locations
                basis = get_basis_functions(part.mesh, self.basis_class)
                Z = self.operator.impedance_matrix(s_start, part)
                lin_s, lin_currents = eig_linearised(Z.L, Z.S, num_modes, basis)
                #print lin_s/2/np.pi

                mode_s = np.empty(num_modes, np.complex128)
                mode_j = np.empty((len(basis), num_modes), np.complex128)

                Z_func = lambda s: self.operator.impedance_matrix(s, part)[:]

                for mode in xrange(num_modes):
                    res = eig_newton(Z_func, lin_s[mode], lin_currents[:, mode],
                                     weight='max element', lambda_tol=1e-8,
                                     max_iter=200)

                    print "Iterations", res['iter_count']
                    #print res['eigval']/2/np.pi
                    mode_s[mode] = res['eigval']
                    j_calc = res['eigvec']
                    mode_j[:, mode] = j_calc/np.sqrt(np.sum(j_calc**2))

                # add to cache
                solved_parts[unique_id] = (mode_s, mode_j)

            all_s.append(mode_s)
            all_j.append(mode_j)

#            all_s.append(lin_s)
#            all_j.append(lin_currents)

        return all_s, all_j

    def construct_models(self, mode_s, mode_j):
        """Construct a scalar model for the modes of each part
        
        Parameters
        ----------
        mode_s : list of ndarray
            The mode frequency of each part
        mode_j : list of ndarray
            The currents for the modes of each part
            
        Returns
        -------
        scalar_models : list
            The scalar models
        """

        solved_parts = {}
        scalar_models = []

        for part_count, part in enumerate(self.parts):
            # TODO: unique ID needs to be modified if different materials or
            # placement above a layer are possible

            unique_id = (part.mesh.id,) # cache identical parts 
            if unique_id in solved_parts:
                #print "got from cache"
                scalar_models.append(solved_parts[unique_id])
            else:
                scalar_models.append([])
                for s_n, j_n in zip(mode_s[part_count], mode_j[part_count].T):
                    Z_func = lambda s: self.operator.impedance_matrix(s, part)[:]                
                    z_der = delta_eig(s_n, j_n, Z_func)
                    #scalar_models.append((s_n, j_n, fit_circuit(s_n, z_der)))
                    scalar_models[-1].append(ScalarModel(s_n, j_n, z_der))

                solved_parts[unique_id] = scalar_models[-1]

            return scalar_models


    def plot_solution(self, solution, output_format, filename=None,
                      compress_scalars=None, compress_separately=False):
        """Plot a solution on several parts"""

        #if output_format

        charges = []
        currents = []
        centres = []
        
        for part_num, part in enumerate(self.parts):
            I = solution[part_num]
            basis = get_basis_functions(part.mesh, self.basis_class)
        
            centre, current, charge = basis.interpolate_function(I, 
                                                return_scalar=True, nodes=part.nodes)
            charges.append(charge.real)
            currents.append(current.real)
            centres.append(centre)
       
        output_format = output_format.lower()
        if output_format == 'mayavi':
            plot_mayavi(self.parts, charges, currents, vector_points=centres,
                       compress_scalars=compress_scalars, filename=filename)
                       
        elif output_format == 'vtk':
            write_vtk(self.parts, charges, currents, filename=filename,
                     compress_scalars=compress_scalars,
                     autoscale_vectors=True,
                     compress_separately=compress_separately)
        else:
            raise ValueError("Unknown output format")

        

#    def circuit_models(self):
#        """
#        """
#        
#
#eig_derivs = []
#
#for part in xrange(n_parts):
#    eig_derivs.append(np.empty(n_modes, np.complex128))
#    for mode in xrange(n_modes):
#        eig_derivs[part][mode] = delta_eig(mode_omega[part][mode], mode_j[part][:, mode], part, loop_star=loop_star)

            