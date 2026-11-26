#!/bin/bash
# Mesh-independence (GCI) study on the wall-resolved meshes, sized for a 4-core laptop.
#
# Three chains run side by side (NPAR=3). Inside a chain the meshes run coarse -> fine and each finer
# mesh starts from the coarser solution (mapFields), which cuts the iterations needed several-fold.
#   single element, h/c 0.224 : levels 1, 2, 3   (~40k, 75k, 140k cells)
#   single element, h/c 0.448 : levels 1, 2, 3   (~45k, 80k, 155k cells)
#   two-element datum, h/c 0.2: levels 1, 2, 3   (~86k, 165k, 330k cells)  - the slow chain
# Expect roughly 6-10 h in total; run it overnight. Re-running skips finished cases.
#
# Usage:  bash run_mesh_study.sh [single|double|all]      then:  python3 gci.py
cd "$(dirname "$0")"
WHICH=${1:-all}; NPAR=${NPAR:-3}
OUT=results_mesh_study.csv
[ -f $OUT ] || echo "config,h_c,level,cells,iters,CL,CD_p,CL_flap,CL_prev" > $OUT
ITERS=${ITERS:-3000}
run_one() {   # config h level  (level>1 starts from level-1)
  local cfg=$1 h=$2 L=$3 name="gci_${1}_h$2_L$3" prev_name="gci_${1}_h$2_L$(( $3 - 1 ))" line cells dir init=""
  if grep -q "^$cfg,$h,$L," $OUT; then echo "  $name already done"; return; fi
  [ $L -gt 1 ] && init=$prev_name
  case $cfg in
    single) line=$(MESH_LEVEL=$L END_TIME=$ITERS INIT_FROM=$init ../cfd2d/run_case.sh $name $h 1 0 0.005 0.15 0.08 2>/dev/null | tail -1); dir=../cfd2d/$name ;;
    datum)  line=$(MESH_LEVEL=$L END_TIME=$ITERS INIT_FROM=$init ../frontwing2d/run_case.sh $name $h 18.93 0 0.005 0.20 0.12 2>/dev/null | tail -1); dir=../frontwing2d/$name ;;
  esac
  local cl cd cf prev
  cl=$(echo "$line" | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p'); cd=$(echo "$line" | sed -n 's/.*Cd_p=\([-0-9.]*\).*/\1/p')
  cf=$(echo "$line" | sed -n 's/.*Cl_flap=\([-0-9.]*\).*/\1/p')
  if [ -z "$cl" ]; then echo "  $name FAILED (see $dir/log.simpleFoam)"; return 1; fi
  cells=$(grep -m1 "cells:" $dir/log.checkMesh | awk '{print $2}')
  prev=$(cd $(dirname $dir) && python3 forces.py $(basename $dir) | tail -2 | head -1 | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p')
  echo "$cfg,$h,$L,$cells,$ITERS,$(awk -v a=$cl 'BEGIN{print -a}'),$cd,$(awk -v a=${cf:-0} 'BEGIN{print -a}'),$(awk -v a=${prev:-0} 'BEGIN{print -a}')" >> $OUT
  echo "  $name  ($cells cells)  C_L = $(awk -v a=$cl 'BEGIN{print -a}')"
}
chain() { for L in 1 2 3; do run_one $1 $2 $L || return; done; }
chains=()
[ "$WHICH" != double ] && chains+=("single 0.224" "single 0.448")
[ "$WHICH" != single ] && chains+=("datum 0.200")
echo "Running ${#chains[@]} chains of 3 meshes, $NPAR chains at a time ..."
start=$(date +%s)
for c in "${chains[@]}"; do
  while [ $(jobs -rp | wc -l) -ge $NPAR ]; do sleep 10; done
  chain $c &
  sleep 2
done
wait
echo "Done in $(( ($(date +%s) - start) / 60 )) min. Now run:  python3 gci.py"
