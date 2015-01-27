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


import numpy as np

from openmodes.constants import epsilon_0, mu_0, pi, c
from openmodes.core import z_mfie_faces_self
from openmodes.basis import LinearTriangleBasis
from openmodes.impedance import ImpedanceMatrix
import logging

from openmodes.operator.operator import Operator, FreeSpaceGreensFunction


def impedance_rwg_mfie_free_space(s, integration_rule, basis_o, nodes_o,
                                  basis_s, nodes_s, normals, self_impedance,
                                  tangential_form):
    """MFIE derived Impedance matrix for RWG or loop-star basis functions"""

    transform_o, _ = basis_o.transformation_matrices
    num_faces_o = len(basis_o.mesh.polygons)

    if self_impedance:
        # calculate self impedance

        num_faces_s = num_faces_o
        Z_faces = z_mfie_faces_self(nodes_o, basis_o.mesh.polygons,
                                    basis_o.mesh.polygon_areas, s,
                                    integration_rule.xi_eta,
                                    integration_rule.weights, normals,
                                    tangential_form)

        transform_s = transform_o

    else:
        # calculate mutual impedance
        raise NotImplementedError

        num_faces_s = len(basis_s.mesh.polygons)

        transform_Z_s, _ = basis_s.transformation_matrices

    if np.any(np.isnan(Z_faces)):
        raise ValueError("NaN returned in impedance matrix")

    Z = transform_o.dot(transform_s.dot(Z_faces.reshape(num_faces_o*3,
                                                        num_faces_s*3,
                                                        order='C').T).T)
    return Z


class MfieOperator(Operator):
    """An operator for the magnetic field integral equation, discretised with
    respect to some set of basis functions. Assumes that Galerkin's method is
    used, such that the testing functions are the same as the basis functions.
    """
    source_field = "magnetic_field"

    def __init__(self, integration_rule, basis_container,
                 greens_function=FreeSpaceGreensFunction(),
                 tangential_form=False, singularity_accuracy=1e-5):
        """
        Parameters
        ----------
        integration_rule: object
        The integration rule over the standard triangle, to be used for all
        non-singular integrals
        basis_container: BasisContainer
        The object which retrieves basis functions for a Part
        tangential_form: boolean
        If True, -n x n x K is solved, otherwise n x K form is used
        """
        self.basis_container = basis_container
        self.integration_rule = integration_rule
        self.greens_function = greens_function

        self.tangential_form = tangential_form
        if tangential_form:
            self.reciprocal = False
            self.source_cross = False
        else:
            self.reciprocal = False
            self.source_cross = True

        logging.info("Creating MFIE operator, tangential form: %s"
                     % str(tangential_form))

    def impedance_single_parts(self, s, part_o, part_s=None):
        """Calculate a self or mutual impedance matrix at a given complex
        frequency

        Parameters
        ----------
        s : complex
            Complex frequency at which to calculate impedance
        part_o : SinglePart
            The observing part, which must be a single part, not a composite
        part_s : SinglePart, optional
            The source part, if not specified will default to observing part
        """

        # if source part is not given, default to observer part
        part_s = part_s or part_o

        basis_o = self.basis_container[part_o]
        basis_s = self.basis_container[part_s]

        normals = basis_o.mesh.surface_normals

        if isinstance(self.greens_function, FreeSpaceGreensFunction):
            if isinstance(basis_o, LinearTriangleBasis):
                Z = impedance_rwg_mfie_free_space(s, self.integration_rule,
                                                  basis_o, part_o.nodes,
                                                  basis_s, part_s.nodes,
                                                  normals,
                                                  part_o == part_s,
                                                  self.tangential_form)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

        return ImpedanceMatrix(s, Z, basis_o, basis_s, self, part_o, part_s)


class TMfieOperator(MfieOperator):
    def __init__(self, **kwargs):
        MfieOperator.__init__(self, tangential_form=True, **kwargs)
