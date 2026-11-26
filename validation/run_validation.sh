#!/bin/bash
# Clean-air validation sweep over ride height for the three Zerihan/Zhang wind-tunnel configurations:
#   single  : single-element wing, reference incidence 1 deg        (h/c with c = 223.4 mm)
#   datum   : two-element wing, datum flap (18.93 deg to main)       (h/c with c = 380 mm)
#   low     : two-element wing, low flap (datum - 8.5 = 10.43 deg)   (h/c with c = 380 mm)
#   plus    : two-element wing, datum + 9.5 deg flap (28.43 deg)     (h/c with c = 380 mm)
# Usage:  bash run_validation.sh [single|datum|low|plus|all]      NPAR=2 runs two cases at a time
# Results are appended to results_validation.csv, or results_validation_L<level>.csv when MESH_LEVEL is set
# (re-running skips cases already done).   Example:  MESH_LEVEL=1 bash run_validation.sh single
cd "$(dirname "$0")"
WHICH=${1:-all}; NPAR=${NPAR:-2}
L=${MESH_LEVEL:-0}; export MESH_LEVEL=$L            # MESH_LEVEL=1 for the wall-resolved production mesh
HS_SINGLE="0.067 0.090 0.112 0.134 0.179 0.224 0.291 0.358 0.448 0.671"
HS_DOUBLE="0.060 0.079 0.100 0.125 0.150 0.200 0.250 0.300 0.400 0.500"
OUT=results_validation.csv; [ "$L" != 0 ] && OUT=results_validation_L$L.csv
[ -f $OUT ] || echo "config,h_c,CL,CD_p,CL_flap" > $OUT
run_one() {   # config h
  local cfg=$1 h=$2 name="val_${1}_h$2" line; [ "$L" != 0 ] && name="${name}_L$L"
  if grep -q "^$cfg,$h," $OUT; then echo "  $name already done"; return; fi
  case $cfg in
    single) line=$(../cfd2d/run_case.sh $name $h 1 0 0.005 0.15 0.08 2>/dev/null | tail -1) ;;
    datum)  line=$(../frontwing2d/run_case.sh $name $h 18.93 0 0.005 0.20 0.12 2>/dev/null | tail -1) ;;
    low)    line=$(../frontwing2d/run_case.sh $name $h 10.43 0 0.005 0.20 0.12 2>/dev/null | tail -1) ;;
    plus)   line=$(../frontwing2d/run_case.sh $name $h 28.43 0 0.005 0.20 0.12 2>/dev/null | tail -1) ;;
  esac
  local cl cd cf
  cl=$(echo "$line" | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p'); cd=$(echo "$line" | sed -n 's/.*Cd_p=\([-0-9.]*\).*/\1/p')
  cf=$(echo "$line" | sed -n 's/.*Cl_flap=\([-0-9.]*\).*/\1/p')
  if [ -z "$cl" ]; then echo "  $name FAILED (see its log.simpleFoam)"; return; fi
  echo "$cfg,$h,$(awk -v a="$cl" 'BEGIN{print -a}'),$cd,$(awk -v a="${cf:-0}" 'BEGIN{print -a}')" >> $OUT
  echo "  $name  C_L = $(awk -v a="$cl" 'BEGIN{print -a}')"
}
jobs_list=()
for cfg in single datum low plus; do
  [ "$WHICH" = all ] || [ "$WHICH" = $cfg ] || continue
  hs=$HS_DOUBLE; [ $cfg = single ] && hs=$HS_SINGLE
  for h in $hs; do jobs_list+=("$cfg $h"); done
done
echo "Running ${#jobs_list[@]} cases, $NPAR at a time ..."
start=$(date +%s)
for j in "${jobs_list[@]}"; do
  while [ $(jobs -rp | wc -l) -ge $NPAR ]; do sleep 5; done
  run_one $j &
  sleep 1
done
wait
echo "Done in $(( ($(date +%s) - start) / 60 )) min. Now run:  python3 plot_validation.py"
