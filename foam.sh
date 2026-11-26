#!/bin/bash
# foam.sh -- run OpenFOAM commands either natively or inside the OpenFOAM Docker image.
#
#   ./foam.sh "<commands>"   run a shell command string with the OpenFOAM environment loaded,
#                            in the current directory (e.g. ./foam.sh "checkMesh -case myCase")
#   ./foam.sh --info         show which OpenFOAM will be used, and its version
#
# Mode is chosen automatically:
#   native  if an OpenFOAM installation is found on this machine (/usr/lib/openfoam/...)
#   docker  otherwise, using the first local image whose name contains "openfoam"
# Overrides:  FOAM_MODE=native|docker   FOAM_IMAGE=opencfd/openfoam-default:2606
#             FOAM_BASHRC=/path/to/etc/bashrc (native)
#
# Docker notes: the current directory is mounted at /work inside the container, so every
# path in the command must be relative to (and inside) the current directory.

# shell snippet that loads the OpenFOAM environment wherever it is installed
LOADER='for f in "$FOAM_BASHRC" /usr/lib/openfoam/openfoam*/etc/bashrc /openfoam/*/etc/bashrc /opt/openfoam*/etc/bashrc /usr/share/openfoam/etc/bashrc; do
  if [ -n "$f" ] && [ -f "$f" ]; then . "$f" >/dev/null 2>&1; [ -n "$WM_PROJECT_DIR" ] && break; fi
done'

find_native() {
  [ -n "$FOAM_BASHRC" ] && [ -f "$FOAM_BASHRC" ] && return 0
  local f
  for f in /usr/lib/openfoam/openfoam*/etc/bashrc /usr/share/openfoam/etc/bashrc; do [ -f "$f" ] && return 0; done
  return 1
}
find_image() {
  [ -n "$FOAM_IMAGE" ] && { echo "$FOAM_IMAGE"; return; }
  docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -i 'openfoam' | grep -v '<none>' | head -1
}
mode=${FOAM_MODE:-}
if [ -z "$mode" ]; then
  if find_native; then mode=native
  elif command -v docker >/dev/null 2>&1; then mode=docker
  else
    echo "foam.sh: no OpenFOAM found. Install it, or install Docker Desktop and turn on" >&2
    echo "         WSL integration for Ubuntu (Settings > Resources > WSL integration)." >&2
    exit 1
  fi
fi

run_native() { FOAM_BASHRC="$FOAM_BASHRC" bash -c "$LOADER"$'\n'"$1"; }
run_docker() {
  local img; img=$(find_image)
  if [ -z "$img" ]; then
    echo "foam.sh: Docker works but no OpenFOAM image was found (docker images | grep openfoam)." >&2
    echo "         Pull one, e.g.  docker pull opencfd/openfoam-default:2606" >&2
    exit 1
  fi
  local base=(docker run --rm -i --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work)
  if [ "$(cat "$HOME/.foam_docker_entry" 2>/dev/null)" = image ]; then
    # let the image's own entrypoint (/openfoam/run) load the environment
    "${base[@]}" "$img" bash -c "$LOADER"$'\n'"$1"
  else
    "${base[@]}" --entrypoint /bin/bash "$img" -c "$LOADER"$'\n'"$1"
  fi
}

if [ "$1" = "--info" ]; then
  cmd='if [ -n "$WM_PROJECT_DIR" ]; then echo "OpenFOAM $WM_PROJECT_VERSION ($WM_PROJECT_DIR)"; else echo "OpenFOAM environment NOT found"; exit 1; fi'
  if [ "$mode" = docker ]; then
    img=$(find_image)
    if [ -z "$img" ]; then
      echo "mode: docker, but no OpenFOAM image found." >&2
      echo "  In Ubuntu, 'docker images' must list your opencfd/openfoam-... image. If docker is not found or shows" >&2
      echo "  nothing, turn on Docker Desktop > Settings > Resources > WSL integration > Ubuntu, then reopen Ubuntu." >&2
      exit 1
    fi
    echo "mode: docker, image: $img"
    rm -f "$HOME/.foam_docker_entry"
    if ! run_docker "$cmd" 2>/dev/null; then          # fall back to the image's own entrypoint
      echo image > "$HOME/.foam_docker_entry"; run_docker "$cmd"; exit $?
    fi
  else echo "mode: native"; run_native "$cmd"; fi
  exit $?
fi
[ -z "$1" ] && { sed -n 2,16p "$0"; exit 1; }
if [ "$mode" = docker ]; then run_docker "$1"; else run_native "$1"; fi
