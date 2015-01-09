package require sqlite3
package require Tclx

proc cleanup {} {
  global sigterm
  set sigterm 1
  puts "received SIGTERM"
}

set sigterm 0
signal trap SIGTERM cleanup

set db_collisions 0

proc db_locked {something} {
  incr db_collisions

  if {$db_collisions % 100 == 0} {
    puts "$db_collisions database collsions"
  }

  return 0 ;#0=retry, 1=abandon
}

sqlite3 db simulation.db
db busy db_locked

set id [lindex $argv 0]
db eval {SELECT * FROM parameters WHERE id = $id} {}

set seconds_per_increment 30
set framelength           1

set output_folder "./$id"

exec ls >& /dev/null

if {![file isdirectory "$output_folder"]} {
  file mkdir "$output_folder"
  puts "redirecting output to $output_folder/log.txt"
  close stdout
  open "$output_folder/log.txt" w
  close stderr
  open "$output_folder/log.txt" w
} else {
  puts "output folder already exists, aborting"
  exit 1000
}

puts "agrid $agrid"
puts "density_salt $density_salt"
puts "box_l $box_l"
puts "ext_force $ext_force"
puts "dt $dt"
puts "use_nonlinear_stencil $use_nonlinear_stencil"
puts "density_solution $density_solution"
puts "D_pos $D_pos"
puts "D_neg $D_neg"
puts "viscosity_kinematic $viscosity_kinematic"
puts "charge $charge"
puts "sphere_radius $sphere_radius"
puts "bjerrum_length $bjerrum_length"
puts "scaling_factor $scaling_factor"
puts ""

set viscosity_kinematic_scaled [expr $viscosity_kinematic / $scaling_factor]
set D_pos_scaled [expr $D_pos * $scaling_factor]
set D_neg_scaled [expr $D_neg * $scaling_factor]
puts "viscosity_kinematic_scaled $viscosity_kinematic_scaled"
puts "D_pos_scaled $D_pos_scaled"
puts "D_neg_scaled $D_neg_scaled"
puts ""

setmd box_l $box_l $box_l $box_l
setmd time_step $dt
setmd skin 0.1

electrokinetics agrid $agrid lb_density $density_solution viscosity $viscosity_kinematic_scaled friction 1.0 T 1 bjerrum_length $bjerrum_length use_nonlinear_stencil $use_nonlinear_stencil

electrokinetics 2 density $density_salt D $D_neg_scaled valency -1.0 ext_force [expr -1.0*$ext_force] 0.0 0.0
electrokinetics 1 density $density_salt D $D_pos_scaled valency 1.0 ext_force [expr $ext_force] 0.0 0.0
electrokinetics boundary net_charge $charge sphere center [expr $box_l / 2.] [expr $box_l / 2.] [expr $box_l / 2.] radius $sphere_radius direction outside
electrokinetics 1 neutralize_system

set runtime_start [clock seconds]
set t 0.0
set step_count 0

electrokinetics print boundary vtk "$output_folder/boundary.vtk"

for {set i 1} {1} {incr i} {
  puts "t = $t"
  puts "step_count = $step_count"
  
  set t0 [clock seconds]
  integrate $framelength
  set t1 [clock seconds]
  set t [expr $t + $framelength * $dt]
  incr step_count $framelength
  
  electrokinetics 1 print density vtk "$output_folder/density_pos.vtk"
  electrokinetics 1 print flux vtk "$output_folder/flux_pos.vtk"
  electrokinetics 2 print density vtk "$output_folder/density_neg.vtk"
  electrokinetics 2 print flux vtk "$output_folder/flux_neg.vtk"
  electrokinetics print velocity vtk "$output_folder/velocity.vtk"
  electrokinetics print lbforce vtk "$output_folder/lbforce.vtk"
  electrokinetics print potential vtk "$output_folder/potential.vtk"
  
  if {[catch {exec grep -i -q nan "$output_folder/density_pos.vtk" "$output_folder/density_neg.vtk" "$output_folder/velocity.vtk"}] != 1} {
    puts "grep found NAN or failed"
    exit 1002
  }
  
  set vx_corner [expr [lindex [electrokinetics node 0 0 0 print velocity] 0] / $scaling_factor]
  set runtime [expr [clock seconds]-$runtime_start]
  db eval {INSERT INTO observables(parameters_id, t, vx_corner, vx_slice, runtime) values($id, $t, $vx_corner, NULL, $runtime)}

  if {$t1-$t0 > 0} {
    set framelength [expr int(ceil(double($seconds_per_increment) / ($t1-$t0) * $framelength))]
  } else {
    set framelength [expr $framelength * 10]
  }
  
  if { $framelength < 1 } {
    set framelength 1
  }

  if {$sigterm} {
    exit 1001
  }

  puts "next framelength = $framelength"
  puts ""
  flush stdout
}

db close
exit 0
