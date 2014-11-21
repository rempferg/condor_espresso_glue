#!/usr/bin/env python

import time
import os
import platform
import shutil
import sqlite3
import subprocess
import sys

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
    
    while True:
      if(p.returncode is None): #running
        vx = query('SELECT vx_corner FROM observables WHERE parameters_id = ? ORDER BY t DESC LIMIT 0,1', (parameters[0],)).fetchone()

        if vx is None:
          continue

        vx = vx[0]

        print 'vx =', vx, '>?', 0.0005

        if(vx > 0.0005):
          print 'yes'
          query('UPDATE parameters SET status = ?, end_time = ? WHERE id = ?', ('done', time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
          p.terminate()
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
