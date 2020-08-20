'''
Stanley Bak
Python Version of F-16 GCAS
ODE derivative code (controlled F16)
'''

from math import sin, cos

import numpy as np
from numpy import deg2rad

from aerobench.lowlevel.subf16_model import subf16_model
from aerobench.lowlevel.low_level_controller import LowLevelController
from aerobench.highlevel.autopilot import Autopilot

def controlled_f16(t, x_f16, autopilot, f16_model='morelli'):
    'returns the LQR-controlled F-16 state derivatives and more'

    assert isinstance(x_f16, np.ndarray)
    assert isinstance(autopilot, Autopilot), "autopilot type was {}".format(type(autopilot))
    assert isinstance(autopilot.llc, LowLevelController)

    assert f16_model in ['stevens', 'morelli'], 'Unknown F16_model: {}'.format(f16_model)

    llc = autopilot.llc

    # Get Reference Control Vector (commanded Nz, ps, Ny + r, throttle)
    u_ref = autopilot.get_u_ref(t, x_f16) # in g's & rads / sec

    x_ctrl, u_deg = llc.get_u_deg(u_ref, x_f16)

    # Note: Control vector (u) for subF16 is in units of degrees
    xd_model, Nz, Ny, _, _ = subf16_model(x_f16[0:13], u_deg, f16_model)

    # Nonlinear (Actual): ps = p * cos(alpha) + r * sin(alpha)
    ps = x_ctrl[4] * cos(x_ctrl[0]) + x_ctrl[5] * sin(x_ctrl[0])

    # Calculate (side force + yaw rate) term
    Ny_r = Ny + x_ctrl[5]

    xd = np.zeros((x_f16.shape[0],))
    xd[:len(xd_model)] = xd_model

    # integrators from low-level controller
    start = len(xd_model)
    end = start + llc.get_num_integrators()
    int_der = llc.get_integrator_derivatives(t, x_f16, u_ref, x_ctrl, Nz, Ny)

    xd[start:end] = int_der

    # integrators from autopilot
    start = end
    end = start + autopilot.get_num_integrators()
    xd[start:end] = autopilot.get_integrator_derivatives(t, x_f16, u_ref, x_ctrl, Nz, Ny)

    # Convert all degree values to radians for output
    u_rad = np.zeros((7,)) # throt, ele, ail, rud, Nz_ref, ps_ref, Ny_r_ref

    u_rad[0] = u_deg[0] # throttle

    for i in range(1, 4):
        u_rad[i] = deg2rad(u_deg[i])

    u_rad[4:7] = u_ref[0:3] # inner-loop commands are 4-7

    return xd, u_rad, Nz, ps, Ny_r