#!/usr/bin/env python

import numpy as np
import os
import sqlite3
import sys
import time

#molarity given in experiments applies to both species individually
#0.006022 particles/nm^3 = 10 mmol/liter (Nadanai Laohakunakorn)
density_salt = [ 0.0
                 #0.0006022,
                 #0.001904,
                 #0.006022,
                 #0.01904,
                 #0.06022,
                 #0.1904
               ]

box_l = [16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 192]
#box_l = [48]

#ext_force = [0.3162, 0.01, 0.03162, 0.1, 0.0, 1.0]
ext_force = [0.01]

agrid = 1.0
dt = 0.2
use_nonlinear_stencil = 0

#997.0751 kg/m^3 = 26.1151 (Wikipedia, water at 25 deg celcius)
density_solution = [26.1151]
bjerrum_length = 0.7095

#for KCl in water: D = 1.33e-9 m^2/s (Christian, Stefan), eta = 1.002 mPa*s (Wikipedia, water at 20 deg celcius)
#D * eta needs to be matched with experiments to get right ratio of convective to diffusive transport
viscosity_dynamic = 79.6984
viscosity_kinematic = [round(viscosity_dynamic / dens , 4) for dens in density_solution]
scaling_factor = viscosity_kinematic * np.ones(len(density_solution))

D_pos = 0.00303681
D_neg = 0.00303681
#D_pos = 0.00403896
#D_neg = 0.00403896
#D_pos = 0.3224
#D_neg = 0.3224

#sphere
charge = -30
sphere_radius = 4

#determine simulation directory and create if necessary
if len(sys.argv) == 2:
  results_dir = sys.argv[1]
else:
  results_dir = time.strftime("%Y-%m-%d_%H-%M")

if not os.path.isdir(results_dir):
  os.mkdir(results_dir)

os.chdir(results_dir)

#create simulation database and initialize parameter table
db = sqlite3.connect('simulation.db')

sql = 'CREATE TABLE IF NOT EXISTS parameters(\
 id INTEGER PRIMARY KEY,\
 status varchar,\
 host varchar,\
 start_time text,\
 end_time text,\
 vx FLOAT,\
 vx_err FLOAT,\
 vx_fit FLOAT,\
 vx_fit_stderr FLOAT,\
 agrid FLOAT,\
 density_salt FLOAT,\
 box_l FLOAT,\
 ext_force FLOAT,\
 dt FLOAT,\
 use_nonlinear_stencil int,\
 density_solution FLOAT,\
 D_pos FLOAT,\
 D_neg FLOAT,\
 viscosity_kinematic FLOAT,\
 charge FLOAT,\
 sphere_radius FLOAT,\
 bjerrum_length FLOAT,\
 scaling_factor FLOAT\
 )'

db.execute(sql)

sql = 'CREATE TABLE IF NOT EXISTS observables(\
 parameters_id INTEGER,\
 t FLOAT,\
 vx_corner FLOAT,\
 vx_slice FLOAT,\
 runtime int\
 )'

db.execute(sql)

for c in density_salt:
  for l in box_l:
    for f in ext_force:
      for i in range(len(density_solution)):
        if len(db.execute('SELECT id FROM parameters where agrid = ? and density_salt = ? and box_l = ? and ext_force = ? and dt = ? and use_nonlinear_stencil = ? and density_solution = ? and D_pos = ? and D_neg = ? and viscosity_kinematic = ? and charge = ? and sphere_radius = ? and bjerrum_length = ? and scaling_factor = ?', (agrid, c, l, f, dt, use_nonlinear_stencil, density_solution[i], D_pos, D_neg, viscosity_kinematic[i], charge, sphere_radius, bjerrum_length, scaling_factor[i])).fetchall()) == 0:
          db.execute('INSERT INTO parameters(id, status, host, start_time, end_time, agrid, density_salt, box_l, ext_force, dt, use_nonlinear_stencil, density_solution, D_pos, D_neg, viscosity_kinematic, charge, sphere_radius, bjerrum_length, scaling_factor) VALUES(NULL, \'waiting\', NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (agrid, c, l, f, dt, use_nonlinear_stencil, density_solution[i], D_pos, D_neg, viscosity_kinematic[i], charge, sphere_radius, bjerrum_length, scaling_factor[i]))

db.commit()
db.close()
