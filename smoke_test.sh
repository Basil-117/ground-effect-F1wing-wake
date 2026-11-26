#!/bin/bash
# Checks the installation: one front-wing CFD case (5-15 min).
# Usage:  bash smoke_test.sh
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
ok=1
echo "== Python libraries"
$PY -c "import gmsh, numpy, scipy, pandas, sklearn, SALib, statsmodels; print('   ok')" || ok=0
echo "== OpenFOAM"
./foam.sh --info 2>&1 | sed "s/^/   /"; [ ${PIPESTATUS[0]} = 0 ] || ok=0
echo "== Front-wing CFD case (h/c 0.15, flap 22 deg, 20% wake deficit) - takes 5-15 minutes"
start=$(date +%s)
cd frontwing2d && rm -rf smoke smoke.msh
out=$(./run_case.sh smoke 0.15 22 0.20 0.05 0.20 0.12 2>&1 | tail -3)
echo "$out" | sed "s/^/   /"; echo "   ($(( $(date +%s) - start )) s)"
cl=$(echo "$out" | sed -n 's/.*Cl=\([-0-9.]*\).*/\1/p')
if [ -n "$cl" ] && awk -v c="$cl" 'BEGIN{exit !(c < -1.5 && c > -4.5)}'; then
  echo "   ok - downforce coefficient $cl is in the expected range (the reference run gave -2.76)"
else
  echo "   FAILED - check frontwing2d/smoke/log.simpleFoam"; ok=0
fi
echo
[ $ok = 1 ] && echo "ALL GOOD - your setup works." || echo "Something failed - copy the output above and send it to me."
