#!/bin/bash
# Dirty-air campaign, single-element wing, production mesh (level 1, wall-resolved) with the wake-carrying
# refinement upstream.  For every case it first runs the same wake through an EMPTY domain (no wing,
# ~1-2 min) and measures what the wing would see (probe.py), then runs the wing itself.
#
# Usage:  bash run_campaign.sh [clean|oat|lhs|all]        (default all = 56 cases, ~16 h with NPAR=3 on 4 cores)
#         suggested: night 1  bash run_campaign.sh clean && bash run_campaign.sh oat     (~5 h)
#                    night 2  bash run_campaign.sh lhs                                    (~12 h)
# Re-running skips finished cases, so it is safe to stop (Ctrl-C) and start again.
# Results: results_campaign.csv     then:  python3 analyse_campaign.py
# Other designs:  DESIGN=checks.csv OUT=results_checks.csv bash run_campaign.sh all   (an optional 8th column
#                 in the design file sets the inlet turbulence length scale in metres; default 0.05)
cd "$(dirname "$0")"
WHICH=${1:-all}; NPAR=${NPAR:-3}; ITERS=${ITERS:-2000}
export MESH_LEVEL=${MESH_LEVEL:-1} WAKE_REFINE=1
C=0.2234
DESIGN=${DESIGN:-campaign.csv}; [ -f $DESIGN ] || python3 doe_campaign.py > /dev/null
OUT=${OUT:-results_campaign.csv}
[ -f $OUT ] || echo "case,set,hc,D,TI,dy_c,sigma_c,cells,CL,CD_p,CL_prev,q_ratio,u_ratio,angle_deg,TI_wing,shear" > $OUT
run_one() {
  local case set hc D TI dy sg lt yc sig probe line cl cd prev cells
  IFS=, read case set hc D TI dy sg lt <<< "$1"
  export TURB_L=${lt:-0.05}
  if grep -q "^$case," $OUT; then echo "  $case already done"; return; fi
  yc=$(awk -v h=$hc -v d=$dy -v c=$C 'BEGIN{printf "%.5f", (h + 0.071 + d) * c}')    # wake centre height [m]
  sig=$(awk -v s=$sg -v c=$C 'BEGIN{printf "%.5f", s * c}')
  # 1) empty domain: the flow the wing would meet
  NO_WING=1 END_TIME=1000 ./run_case.sh ${case}_empty $hc 1 $D $TI $yc $sig > /dev/null 2>&1
  probe=$(python3 probe.py ${case}_empty $hc --csv 2>/dev/null | tail -1)
  [ -z "$probe" ] && probe=",,,,"
  [ "${KEEP_EMPTY:-0}" = 1 ] || rm -rf ${case}_empty ${case}_empty.msh
  # 2) the wing
  line=$(END_TIME=$ITERS ./run_case.sh $case $hc 1 $D $TI $yc $sig 2>/dev/null | tail -1)
  rm -f $case.msh
  cl=$(echo "$line" | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p'); cd=$(echo "$line" | sed -n 's/.*Cd_p=\([-0-9.]*\).*/\1/p')
  if [ -z "$cl" ]; then echo "  $case FAILED (see cfd2d/$case/log.simpleFoam)"; return; fi
  prev=$(python3 forces.py $case | tail -2 | head -1 | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p')
  cells=$(grep -m1 "cells:" $case/log.checkMesh | awk '{print $2}')
  echo "$case,$set,$hc,$D,$TI,$dy,$sg,$cells,$(awk -v a=$cl 'BEGIN{print -a}'),$cd,$(awk -v a=${prev:-0} 'BEGIN{print -a}'),$probe" >> $OUT
  echo "  $case [$set] h/c=$hc D=$D TI=$TI dy=$dy  ->  C_L = $(awk -v a=$cl 'BEGIN{print -a}')   q_wing/q_inf = ${probe%%,*}"
}
mapfile -t rows < <(tail -n +2 $DESIGN | awk -F, -v w=$WHICH 'w=="all" || $2==w')
echo "Running ${#rows[@]} cases ($WHICH), $NPAR at a time, $ITERS iterations each, mesh level $MESH_LEVEL ..."
start=$(date +%s)
for r in "${rows[@]}"; do
  while [ $(jobs -rp | wc -l) -ge $NPAR ]; do sleep 10; done
  run_one "$r" &
  sleep 2
done
wait
echo "Done in $(( ($(date +%s) - start) / 60 )) min.  Now run:  python3 analyse_campaign.py"
