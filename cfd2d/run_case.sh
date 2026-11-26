#!/bin/bash
# run_case.sh <case> <h/c> <alpha> <D> <TI> <yc> <sigma> [upwash_deg]   (single-element wing, serial)
# Python (mesh + case files) runs here; OpenFOAM runs natively or in Docker via ../foam.sh
# Environment: MESH_LEVEL, END_TIME, NUMERICS, INIT_FROM (see below), WAKE_REFINE=1, OPEN_TOP=1,
#              NO_WING=1 (empty-domain run: no wing, prints nothing - read it with probe.py)
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}; FOAM="$(cd .. && pwd)/foam.sh"
case=$1
rm -rf "$case" "$case.msh"          # always start from a clean case folder
# INIT_FROM=<finished case in this folder>: start from its solution (mapFields)
MAPCMD=""; [ -n "$INIT_FROM" ] && MAPCMD="mapFields ../$INIT_FROM -consistent -sourceTime latestTime > log.mapFields 2>&1 &&"
WALLS="wing ground"; [ "$NO_WING" = 1 ] && WALLS="ground"
$PY mesh.py $2 $3 $case.msh > /dev/null
$PY make_case.py $case $4 $5 $6 $7 ${8:-0} > /dev/null
"$FOAM" "gmshToFoam $case.msh -case $case > $case/log.gmshToFoam 2>&1 && cd $case &&
foamDictionary constant/polyMesh/boundary -entry entry0/frontAndBack/type -set empty > /dev/null &&
for p in $WALLS; do foamDictionary constant/polyMesh/boundary -entry entry0/\$p/type -set wall > /dev/null; done &&
(checkMesh > log.checkMesh 2>&1 || true) && $MAPCMD simpleFoam > log.simpleFoam 2>&1"
touch $case/$case.foam
[ "$NO_WING" = 1 ] || $PY forces.py $case | tail -1
