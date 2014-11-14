#!/usr/bin/env python

import time
import os
import platform
import shutil
import sqlite3
import subprocess
import sys

espresso = 'Espresso'
script = 'sphere_electrophoresis_2.tcl'

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

parameters = db.execute('SELECT * FROM parameters WHERE status = "waiting" ORDER BY id ASC LIMIT 0,1').fetchone()

while parameters != None:
  locked = True
  while locked:
    locked = False
    try:
      status_cur = db.execute('UPDATE parameters SET status = "running", host = ?, start_time = ? WHERE id = ? and status = "waiting"', (platform.uname()[1], time.strftime('%Y-%m-%d %H:%M:%S'), parameters[0]))
      db.commit()
    except sqlite3.OperationalError as e:
      print platform.uname()[1], str(e)
      locked = True

  if status_cur.rowcount != 0:
    p = subprocess.Popen([espresso, script, str(parameters[0])])
    
    while db.execute('SELECT status FROM parameters WHERE id = ?', (parameters[0],)).fetchone()[0] == 'running':
      time.sleep(30)

    p.terminate()

    locked = True
    while locked:
      locked = False
      try:
        db.execute('UPDATE parameters SET end_time = ? WHERE id = ?', (time.strftime('%Y-%m-%d %H:%M:%S'),))
        db.commit()
      except sqlite3.OperationalError as e:
        print platform.uname()[1], str(e)
        locked = True

    parameters = db.execute('SELECT * FROM parameters WHERE status = "waiting" ORDER BY id ASC LIMIT 0,1').fetchone()

db.close()
