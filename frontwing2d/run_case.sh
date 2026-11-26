#!/bin/bash
# run_case.sh <case> <h/c> <flap_deg> <D> <TI> <yc> <sigma> [upwash_deg]   (serial)
# e.g. ./run_case.sh myCase 0.15 22 0.20 0.05 0.20 0.12 2
# Python (mesh + case files) runs here; OpenFOAM runs natively or in Docker via ../foam.sh
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}; FOAM="$(cd .. && pwd)/foam.sh"
case=$1
rm -rf "$case" "$case.msh"          # always start from a clean case folder
# INIT_FROM=<finished case in this folder>: start from its solution (mapFields) - converges much faster on fine meshes
MAPCMD=""; [ -n "$INIT_FROM" ] && MAPCMD="mapFields ../$INIT_FROM -consistent -sourceTime latestTime > log.mapFields 2>&1 &&"
$PY mesh2.py $2 $3 $case.msh > /dev/null
$PY make_case_fw.py $case $4 $5 $6 $7 ${8:-0} > /dev/null
"$FOAM" "gmshToFoam $case.msh -case $case > $case/log.gmshToFoam 2>&1 && cd $case &&
foamDictionary constant/polyMesh/boundary -entry entry0/frontAndBack/type -set empty > /dev/null &&
for p in wing flap ground; do foamDictionary constant/polyMesh/boundary -entry entry0/\$p/type -set wall > /dev/null; done &&
(checkMesh > log.checkMesh 2>&1 || true) && $MAPCMD simpleFoam > log.simpleFoam 2>&1"
touch $case/$case.foam                      # lets ParaView open the case
$PY forces.py $case | tail -1
