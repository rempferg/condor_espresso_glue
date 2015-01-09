#!/usr/bin/env python

import MySQLdb
import numpy as np
import os
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
db = MySQLdb.connect(read_default_file='~/.my.cnf')
cur = db.cursor()

sql = 'CREATE TABLE IF NOT EXISTS `%s_parameters` (\
  `id` int(11) NOT NULL AUTO_INCREMENT,\
  `status` varchar(20) NOT NULL,\
  `host` varchar(255) NULL,\
  `start_time` datetime NULL,\
  `end_time` datetime NULL,\
  `vx` float NULL,\
  `vx_err` float NULL,\
  `vx_fit` float NULL,\
  `vx_fit_stderr` float NULL,\
  `agrid` float NOT NULL,\
  `density_salt` float NOT NULL,\
  `box_l` float NOT NULL,\
  `ext_force` float NOT NULL,\
  `dt` float NOT NULL,\
  `use_nonlinear_stencil` int(11) NOT NULL,\
  `density_solution` float NOT NULL,\
  `D_pos` float NOT NULL,\
  `D_neg` float NOT NULL,\
  `viscosity_kinematic` float NOT NULL,\
  `charge` float NOT NULL,\
  `sphere_radius` float NOT NULL,\
  `bjerrum_length` float NOT NULL,\
  `scaling_factor` float NOT NULL,\
  PRIMARY KEY (`id`)\
  );' % (results_dir,)

cur.execute(sql)

sql = 'CREATE TABLE IF NOT EXISTS `%s_observables`(\
 `parameters_id` int(11),\
 `t` FLOAT,\
 `vx_corner` FLOAT,\
 `vx_slice` FLOAT,\
 `runtime` int(11)\
 )' % (results_dir,)

cur.execute(sql)

for c in density_salt:
  for l in box_l:
    for f in ext_force:
      for i in range(len(density_solution)):
        if cur.execute('SELECT id FROM `%s_parameters` where agrid = %s and density_salt = %s and box_l = %s and ext_force = %s and dt = %s and use_nonlinear_stencil = %s and density_solution = %s and D_pos = %s and D_neg = %s and viscosity_kinematic = %s and charge = %s and sphere_radius = %s and bjerrum_length = %s and scaling_factor = %s' % (results_dir, agrid, c, l, f, dt, use_nonlinear_stencil, density_solution[i], D_pos, D_neg, viscosity_kinematic[i], charge, sphere_radius, bjerrum_length, scaling_factor[i])) == 0:
          cur.execute('INSERT INTO `%s_parameters`(id, status, host, start_time, end_time, agrid, density_salt, box_l, ext_force, dt, use_nonlinear_stencil, density_solution, D_pos, D_neg, viscosity_kinematic, charge, sphere_radius, bjerrum_length, scaling_factor) VALUES(NULL, \'waiting\', NULL, NULL, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)' % (results_dir, agrid, c, l, f, dt, use_nonlinear_stencil, density_solution[i], D_pos, D_neg, viscosity_kinematic[i], charge, sphere_radius, bjerrum_length, scaling_factor[i]))

cur.close()
db.commit()
db.close()
