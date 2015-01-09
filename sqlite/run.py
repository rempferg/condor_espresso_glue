#!/usr/bin/env python

import numpy as np
import os
import platform
import scipy.optimize
import shutil
import sqlite3
import subprocess
import sys
import time

espresso = 'Espresso'
script = 'sphere_electrophoresis_4.tcl'

os.environ['PATH'] = '/home/georg/tcl8.6.2/bin:/home/georg/bin:/home/georg/usr/bin:/usr/local/cuda/bin:/usr/bin:/usr/lib64/mpi/gcc/openmpi/bin:/home/georg/bin:/usr/local/bin:/usr/bin:/bin:/usr/bin/X11:/usr/X11R6/bin:/usr/games:/opt/kde3/bin:/usr/lib/mit/bin:/usr/lib/mit/sbin'
os.environ['LD_LIBRARY_PATH'] = '/home/georg/tcl8.6.2/lib:/usr/lib64/mpi/gcc/openmpi/lib64:/home/georg/usr/lib64:/opt/google/chrome:/usr/local/cuda/lib64'

if len(sys.argv) != 2:
  print 'No simulation directory specified'
  exit(1)
else:
  simulation_dir = sys.argv[1]

if not os.path.isdir(simulation_dir):
  print 'Simulation directory doesn\'t exist'
  exit(1)
else:
  os.chdir(simulation_dir)

cuda_fail = subprocess.call(['nvidia-smi'])
lock_fail = subprocess.call(['flock', platform.uname()[1], '-c', 'echo'])
os.remove(platform.uname()[1])

if cuda_fail != 0 or lock_fail != 0:
  if not os.path.isdir('failures'):
    os.mkdir('failures')

  if cuda_fail != 0:
    with open("failures/%s_cuda" % (platform.uname()[1],), 'a') as f:
      f.write(time.strftime("%Y-%m-%d %H:%M:%S") + '\n')

  if lock_fail != 0:
    with open("failures/%s_lock" % (platform.uname()[1],), 'a') as f:
      f.write(time.strftime("%Y-%m-%d %H:%M:%S") + '\n')

  time.sleep(180)
  exit(1)

if not os.path.isfile(script):
  shutil.copy('../' + script, './' + script)

db = sqlite3.connect('simulation.db')

def query(sql, parameters=()):
  global db

  locked = True

  while locked:
    locked = False

    try:
      ret = db.execute(sql, parameters)
      db.commit()
    except sqlite3.OperationalError as e:
      print platform.uname()[1], str(e)
      locked = True

  return ret

parameters = query('SELECT * FROM parameters WHERE status = "waiting" ORDER BY id ASC LIMIT 0,1').fetchone()

while parameters != None:
  status_cur = query('UPDATE parameters SET status = "running", host = ?, start_time = ? WHERE id = ? and status = "waiting"', (platform.uname()[1], time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))

  if status_cur.rowcount != 0:
    p = subprocess.Popen([espresso, script, str(parameters[0])])
    
    popt = None

    while True:
      if(p.returncode is None): #running
        vx = query('SELECT t, vx_corner FROM observables, parameters WHERE parameters_id = id and parameters_id = ? and t*t >= box_l*box_l/(72*3.141592654*bjerrum_length*density_salt*min(D_pos,D_neg)*min(D_pos,D_neg)) ORDER BY t', (parameters[0],)).fetchall()

        if not vx:
          continue

        vx = np.array(vx).T

        if len(vx[0]) >= 2:
          if popt is None:
            popt = [vx[1][-1], 1.0/vx[0][-1]]

          try:
            popt, pcov = scipy.optimize.curve_fit(lambda t,a,b: a*(1.0-np.exp(-b*t)), vx[0], vx[1], popt)
          except Exception as e:
            popt = [vx[1][-1], 1.0/vx[0][-1]]
            print str(e)
          else:
            if pcov is np.inf:
              popt_stderr = [np.inf, np.inf]
            else:
              popt_stderr = np.sqrt(np.diag(pcov))

            vx_abserr = vx[1][-1]-popt[0]
            vx_relerr = vx_abserr / vx[1][-1]

            print
            print 'vx=' + str(vx[1][-1])
            print 'vx_inf=' + str(popt[0]) + '+-' + str(popt_stderr[0])
            print 'relerr=' + str(vx_relerr)
            print 'sigma=' + str(popt_stderr[0])
            print '0.01*vx=' + str(0.01*vx[1][-1]) + '=' + str(abs(0.01*vx[1][-1])/popt_stderr[0]) + 's'

            if abs(vx_relerr) <= 0.01 and 3.0*popt_stderr[0] < abs(0.01*vx[1][-1]):
              print 'vx_relerr=' + str(vx_relerr) + '<0.01 3.0*popt_stderr=' + str(3.0*popt_stderr[0]) + '<' + str(abs(0.01*vx[1][-1])) + '=abs(0.01*vx)'
              query('UPDATE parameters SET status = ?, end_time = ?, vx = ?, vx_err = ?, vx_fit = ?, vx_fit_stderr = ? WHERE id = ?', ('done', time.strftime('%Y-%m-%d %H:%M:%S'), vx[1][-1], vx_abserr, popt[0], popt_stderr[0], parameters[0]))
              p.terminate()
              p.wait()
              break
          
        time.sleep(30)
        continue

      elif(p.returncode == 1001): #sigterm
          query('UPDATE parameters SET set status = ?, end_time = ? WHERE id = ?', ('killed', time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
          break
      elif(p.returncode == 1002): #NaN
          query('UPDATE parameters SET set status = ?, end_time = ? WHERE id = ?', ('NaN', time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
          break
      else: #died
          query('UPDATE parameters SET set status = ?, end_time = ? WHERE id = ?', ('died', time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
          break

    parameters = query('SELECT * FROM parameters WHERE status = "waiting" ORDER BY id ASC LIMIT 0,1').fetchone()

db.close()
