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
script = 'sphere_electrophoresis_3.tcl'

os.environ['PATH'] = '/home/georg/bin:/home/georg/usr/bin:/usr/local/cuda/bin:/home/georg/bin:/home/georg/usr/bin:/usr/local/cuda/bin:/usr/lib64/mpi/gcc/openmpi/bin:/home/georg/bin:/usr/local/bin:/usr/bin:/bin:/usr/bin/X11:/usr/X11R6/bin:/usr/games:/opt/kde3/bin:/usr/lib/mit/bin:/usr/lib/mit/sbin'
os.environ['LD_LIBRARY_PATH'] = '/usr/lib64/mpi/gcc/openmpi/lib64:/home/georg/usr/lib64:/opt/google/chrome:/usr/local/cuda/lib64:/home/georg/usr/lib64:/opt/google/chrome:/usr/local/cuda/lib64'

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

parameters = db.execute('SELECT * FROM parameters WHERE status = "waiting" ORDER BY id ASC LIMIT 0,1').fetchone()

while parameters != None:
  status_cur = query('UPDATE parameters SET status = "running", host = ?, start_time = ? WHERE id = ? and status = "waiting"', (platform.uname()[1], time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))

  if status_cur.rowcount != 0:
    p = subprocess.Popen([espresso, script, str(parameters[0])])
    
    popt = None

    while True:
      if(p.returncode is None): #running
        vx = query('SELECT t, vx_corner FROM observables WHERE parameters_id = ? ORDER BY t', (parameters[0],)).fetchall()

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
            print 'vx=' + str(vx[1][-1]), 'vx_inf=' + str(popt[0]) + '+-' + str(np.sqrt(np.diag(pcov))[0]), 'err=' + str((vx[1][-1]-popt[0])/vx[1][-1]) + '=' + str(abs(vx[1][-1]-popt[0])/np.sqrt(np.diag(pcov))[0]) + 's'
          
        time.sleep(30)
        continue

        if(vx > 0.0005):
          print 'yes'
          query('UPDATE parameters SET status = ?, end_time = ? WHERE id = ?', ('done', time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
          p.terminate()
          p.wait()
          break
        else:
          print 'no'
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
