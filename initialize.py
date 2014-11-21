#!/usr/bin/env python

import sqlite3
import time
import os
import sys

#molarity given in experiments applies to both species individually
#0.006022 particles/nm^3 = 10 mmol/liter (Nadanai Laohakunakorn)
density_salt = [ #0.0006022,
                 #0.001904,
                 0.006022,
                 #0.01904,
                 #0.06022,
                 #0.1904
               ]

box_l = [32, 64, 96, 108, 128]
#box_l = [192, 160, 138, 128, 108, 96, 64, 32]

#ext_force = [0.3162, 0.01, 0.03162, 0.1, 0.0, 1.0]
ext_force = [0.01]

dt = 0.2
use_nonlinear_stencil = 0

#997.0751 kg/m^3 = 26.1151 (Wikipedia, water at 25 deg celcius)
density_solution = [26.1151]

#for KCl in water: D = 1.33e-9 m^2/s (Christian, Stefan), eta = 1.002 mPa*s (Wikipedia, water at 20 deg celcius)
#D * eta needs to be matched with experiments to get right ratio of convective to diffusive transport
D_pos = 0.3224
D_neg = 0.3224

viscosity = 1.0 #rescaled from 79.76 = 1.002 mPa*s

#10e on a sphere covering 56 lattice nodes
charge_density = -0.03571
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
 density_salt FLOAT,\
 box_l FLOAT,\
 ext_force FLOAT,\
 dt FLOAT,\
 use_nonlinear_stencil int,\
 density_solution FLOAT,\
 D_pos FLOAT,\
 D_neg FLOAT,\
 viscosity FLOAT,\
 charge_density FLOAT,\
 sphere_radius FLOAT\
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
      for d in density_solution:
        if len(db.execute('SELECT id FROM parameters where density_salt = ? and box_l = ? and ext_force = ? and dt = ? and use_nonlinear_stencil = ? and density_solution = ? and D_pos = ? and D_neg = ? and viscosity = ? and charge_density = ? and sphere_radius = ?', (c, l, f, dt, use_nonlinear_stencil, d, D_pos, D_neg, viscosity, charge_density, sphere_radius)).fetchall()) == 0:
          db.execute('INSERT INTO parameters(id, status, host, start_time, end_time, density_salt, box_l, ext_force, dt, use_nonlinear_stencil, density_solution, D_pos, D_neg, viscosity, charge_density, sphere_radius) VALUES(NULL, \'waiting\', NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (c, l, f, dt, use_nonlinear_stencil, d, D_pos, D_neg, viscosity, charge_density, sphere_radius))

db.commit()
db.close()
