# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 16:14:29 2013

@author: dap124
"""

import openmodes
#from openmodeimport gmsh
import numpy as np
import scipy.linalg as la
import os.path as osp
import matplotlib.pyplot as plt
from scipy.constants import c

def loop_star_linear_eigenmodes():
    """"Solve the linearised eigenvalue problem in a loop-star basis.
    """
    
    filename = osp.join("geometry", "asymmetric_ring.geo")
    mesh_tol = 1e-3
    
    meshed_name = gmsh.mesh_geometry(filename, mesh_tol)
    (nodes1, triangles1), (nodes2, triangles2) = gmsh.read_mesh(meshed_name, split_geometry=True)
    ring1 = openmodes.sim_object(nodes1, triangles1)
    ring2 = openmodes.sim_object(nodes2, triangles2)
    
    sim = openmodes.MOM_simulation(integration_rule = 10)
    sim.add_object(ring1)
    sim.add_object(ring2)
   
    freq = 7e9
    omega = 2*np.pi*freq
    s = 1j*omega

    L, S = sim.impedance_matrix(s)
    V = sim.source_term(omega, [0, 1, 0], [0, 0, 0])

    I = la.solve(s*L + S/s, V)

    power = np.dot(V.conj(), I)

    n_modes = 20

    w, vr = sim.linearised_eig(L, S, n_modes)

    power_modes = np.empty(n_modes, np.complex128)

    for mode in xrange(n_modes):

        S_mode = np.dot(vr[:, mode], np.dot(S, vr[:, mode]))
        L_mode = np.dot(vr[:, mode], np.dot(L, vr[:, mode]))
        power_modes[mode] = s*np.dot(vr[:, mode], V)*np.dot(vr[:, mode], V.conj())/(S_mode+s**2*L_mode)

    print power, sum(power_modes)
    print power_modes
 
def srr_coupling():
    """
    Calculate coupling coefficients for a pair of SRRs
    """

    #filename = osp.join("geometry", "dipole.geo")
    #freqs = np.linspace(4e9, 15e9, 201)
    filename = osp.join("geometry", "SRR.geo")
    freqs = np.linspace(2e9, 20e9, 201)

    mesh_tol = 2e-3
    
    sim = openmodes.Simulation()
    
    #meshed_name = gmsh.mesh_geometry(filename, mesh_tol)
    #(nodes, triangles), = gmsh.read_mesh(meshed_name)
    
    #srr = openmodes.LibraryPart(nodes, triangles)
    srr = openmodes.load_parts(filename, mesh_tol)
    
    srr1 = sim.place_part(srr)
    srr2 = sim.place_part(srr)    
    
    #srr2 = srr1.duplicate()
    #separation = [500e-3, 0e-3, 0]
    separation = [0e-3, 50e-3, 0]
    #separation = [0e-3, 150e-3, 0]
    #separation = [150e-3, 0e-3, 0]
    #separation = [15e-3, 15e-3, 0]
    #separation = [0, 10e-3, 0]
    srr2.translate(separation)
    #dipole2.rotate([0, 0, 1], 45)
    
    #sim.add_object(srr1)
    #sim.add_object(srr2)
    
    kappa_e_direct = np.empty(len(freqs), np.complex128)
    kappa_m_direct = np.empty(len(freqs), np.complex128)
    
    n_modes = 2 
    
    
    y_srr = np.empty((len(freqs), n_modes), np.complex128)
    
    for count, freq in enumerate(freqs):
        s = 2j*np.pi*freq
        #jk_0 = s/c
    
        L, S = sim.impedance_matrix(s)

        
        L_self = sim.sub_matrix(L, 0)
        S_self = sim.sub_matrix(S, 0)

        Z_self = s*L_self + S_self/s

        z_all, v_all = la.eig(Z_self)
        which_z = np.argsort(abs(z_all.imag))[:n_modes]
        z_direct = z_all[which_z]
        
        # There is some variation of dipole moment with frequency. However
        # for x separation of dipoles, this is automatically accounted for.
        # For y separation direct calculation of mutual L drops much faster
        # than dipole
        #if count == 0:
        v = v_all[:, which_z]
        v /= np.sqrt(np.sum(v**2, axis=0))

        y_srr[count] = 1.0/z_direct

        #w, v = mom.linearised_eig(L, S, n_modes, which_obj = 0)
        #w, vl, vr = sim.get_eigs(L[r1, r1], S[r1, r1], filter_freq, left=True)



        L_mutual = sim.sub_matrix(L, 0, 1)
        S_mutual = sim.sub_matrix(S, 0, 1)

        L_mut = np.dot(v[:, 0], np.dot(L_mutual, v[:, 0]))
        L_self = np.dot(v[:, 0], np.dot(L_self, v[:, 0]))

        #kappa_m_direct[count] = np.dot(v[:, 0], la.lu_solve(L_lu, np.dot(L_mutual, v[:, 0])))
        kappa_m_direct[count] = L_mut/L_self #1j*omega*L_mut#/(1j*omega*L_self)


        S_mut = np.dot(v[:, 0], np.dot(S_mutual, v[:, 0]))
        S_self = np.dot(v[:, 0], np.dot(S_self, v[:, 0]))
        kappa_e_direct[count] = S_mut/S_self#/omega


    plt.figure()
    plt.plot(freqs*1e-9, kappa_e_direct.real, label="direct real")
    plt.plot(freqs*1e-9, kappa_e_direct.imag, label="direct imag")
    plt.legend()
    plt.title("kappa_e")
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(freqs*1e-9, kappa_m_direct.real, label="direct real")
    plt.plot(freqs*1e-9, kappa_m_direct.imag, label="direct imag")
    plt.legend()
    plt.title("kappa_m")
    plt.show()

    plt.figure()
    plt.plot(freqs*1e-9, y_srr.real)
    plt.plot(freqs*1e-9, y_srr.imag)
    plt.show()

def srr_extinction():
    """
    Calculate the excinction for a pair of SRRs
    """

    filename = osp.join("geometry", "SRR.geo")
    freqs = np.linspace(2e9, 20e9, 201)

    mesh_tol = 2e-3
    srr = openmodes.load_parts(filename, mesh_tol)
    
    sim = openmodes.Simulation()    
    srr1 = sim.place_part(srr)
    srr2 = sim.place_part(srr)    
    
    #separation = [500e-3, 0e-3, 0]
    separation = [20e-3, 0e-3, 0]
    #separation = [0e-3, 150e-3, 0]
    #separation = [150e-3, 0e-3, 0]
    #separation = [15e-3, 15e-3, 0]
    #separation = [0, 10e-3, 0]
    srr2.translate(separation)
    
    e_inc = np.array([1, 1, 0])
    k_hat = np.array([0, 0, 1])
    
    
    #y_srr = np.empty((len(freqs), n_modes), np.complex128)
    extinction = np.empty(len(freqs), np.complex128)
    
    for freq_count, freq in enumerate(freqs):
        s = 2j*np.pi*freq
        jk_0 = s/c        
        
        L, S = sim.impedance_matrix(s)

        V = sim.source_term(e_inc, k_hat*jk_0)
        extinction[freq_count] = np.dot(V.conj(), la.solve(s*L + S/s, V))
        
    plt.figure()
    plt.plot(freqs*1e-9, extinction.real)
    plt.plot(freqs*1e-9, extinction.imag)
    plt.show()


def plot_parts():

    filename = osp.join("geometry", "SRR.geo")

    mesh_tol = 1e-3
    srr = openmodes.load_parts(filename, mesh_tol)

    sim = openmodes.Simulation()    
    srr1 = sim.place_part(srr)
    srr2 = sim.place_part(srr)    
    
    separation = [20e-3, 0e-3, 0]
    srr2.translate(separation)


    import visualise
    visualise.plot_parts(sim._parts)

    
def compare_source_terms():

    import core_for
    #import core_cython

     
    filename = osp.join("geometry", "SRR.geo")
    
    mesh_tol = 0.1e-3
    srr = openmodes.load_parts(filename, mesh_tol)
    
    sim = openmodes.Simulation()    
    sim.place_part(srr)
    
    
    e_inc = np.array([1, 1, 0], dtype=np.complex128)
    k_hat = np.array([0, 0, 1], dtype=np.complex128)
    
    s = 2j*np.pi*1e9
    jk_inc = s/c*k_hat
       
    xi_eta_eval, weights = sim.quadrature_rule
    nodes = sim.nodes
    tri = sim.tri
    basis = sim.basis
        
    
    
    incident = core_for.voltage_plane_wave(nodes, tri.nodes, basis.tri_p, basis.tri_m, basis.node_p, basis.node_m, xi_eta_eval, weights, e_inc, jk_inc)
    #incident2 = core_cython.voltage_plane_wave(nodes, tri.nodes, basis.tri_p, basis.tri_m, basis.node_p, basis.node_m, xi_eta_eval, weights[0], e_inc, jk_inc)
    
    plt.figure()
    plt.plot(incident.real)
    plt.plot(incident.imag)
    plt.plot(incident2.real, '--')
    plt.plot(incident2.imag, '--')
    plt.show()
    



#loop_star_linear_eigenmodes()
#srr_coupling()
srr_extinction()
#plot_parts()
#compare_source_terms()