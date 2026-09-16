#!/usr/bin/env bash
#
# One-shot setup for rtl2gdsagi on Ubuntu/Debian.
#
# Safe to re-run: every step checks whether it is already done. Nothing here
# needs to succeed for the others to work, so a missing optional tool degrades
# a gate rather than breaking the install.
#
#   ./setup.sh          # install everything
#   ./setup.sh --check  # just report what is present
#
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
# /snap/bin goes on PATH too: once cmake is installed via snap (step 1a) it
# must shadow any older apt/system cmake for the rest of this script AND for
# any later manual re-run.
export PATH="$VENV/bin:/snap/bin:$PATH"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
miss() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

# `usermod -aG docker $USER` only takes effect in NEW login sessions — the
# current shell's process credentials don't change until you log out and
# back in. `sg docker -c '...'` runs a single command with the docker group
# active right now instead, so this script (freshly adding the user to the
# group a few lines earlier) can still use docker immediately.
docker_do() {
  if id -nG 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
    "$@"
  else
    sg docker -c "$*"
  fi
}

# version_ge A B -> true if A >= B (dotted version strings)
version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

# Debian/Ubuntu apt yosys is frequently too old for this flow (missing passes /
# stale JSON frontend behavior), so yosys is built from source via CMake
# instead of apt. YOSYS_MIN_VERSION gates whether an apt/existing install is
# accepted as-is or rebuilt.
YOSYS_MIN_VERSION="0.44"
YOSYS_GIT_REF="main"

# Ubuntu 22.04's apt cmake is 3.22.x, but Yosys' own CMake build requires
# 3.28+. CMAKE_MIN_VERSION gates whether we need to fetch a newer cmake via
# snap (the officially recommended route: `sudo snap install cmake --classic`)
# instead of relying on apt.
CMAKE_MIN_VERSION="3.28"

# CUDD is the BDD library OpenSTA links against. Built from source once and
# reused; its install prefix is what OpenSTA's -DCUDD_DIR needs to find it.
CUDD_VERSION="3.0.0"
CUDD_PREFIX="$VENV/opt/cudd-$CUDD_VERSION"

yosys_version() {
  have yosys || return 1
  yosys -V 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -n1
}

yosys_is_recent() {
  local v
  v="$(yosys_version)" || return 1
  [ -n "$v" ] || return 1
  version_ge "$v" "$YOSYS_MIN_VERSION"
}

cmake_version() {
  have cmake || return 1
  cmake --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1
}

cmake_is_recent() {
  local v
  v="$(cmake_version)" || return 1
  [ -n "$v" ] || return 1
  version_ge "$v" "$CMAKE_MIN_VERSION"
}

sta_is_ready() { have sta || [ -x "$VENV/bin/sta" ]; }
cudd_is_ready() { [ -f "$CUDD_PREFIX/lib/libcudd.a" ] || [ -f "$CUDD_PREFIX/lib64/libcudd.a" ]; }

# --------------------------------------------------------------- report ----

report() {
  step "Tools"
  for t in verilator iverilog klayout git; do
    have "$t" && ok "$t" || miss "$t   (apt-get install $t)"
  done
  have pip3 && ok "pip3" || miss "pip3   (apt-get install python3-pip)"
  python3 -c 'import venv' 2>/dev/null && ok "python3-venv" || miss "python3-venv   (apt-get install python3-venv)"

  if cmake_is_recent; then
    ok "cmake $(cmake_version) (>= $CMAKE_MIN_VERSION)"
  elif have cmake; then
    miss "cmake $(cmake_version) is older than $CMAKE_MIN_VERSION (needed to build yosys: sudo snap install cmake --classic)"
  else
    miss "cmake   (sudo snap install cmake --classic)"
  fi

  if yosys_is_recent; then
    ok "yosys $(yosys_version) (>= $YOSYS_MIN_VERSION)"
  elif have yosys; then
    miss "yosys $(yosys_version) is older than $YOSYS_MIN_VERSION (build from source: see step 1b)"
  else
    miss "yosys   (build from source: see step 1b)"
  fi
  have eqy && ok "eqy" || warn "eqy   (optional: formal equivalence; signoff needs it)"
  [ -x "$VENV/bin/sby" ] && ok "sby (in venv)" || warn "sby   (optional: stronger equivalence proofs)"
  [ -x "$VENV/bin/z3" ]  && ok "z3 (in venv)"  || warn "z3    (optional: SMT solver for sby)"

  if cudd_is_ready; then
    ok "cudd $CUDD_VERSION ($CUDD_PREFIX)"
  else
    warn "cudd   (optional but recommended: gives sta BDD support; built automatically in step 2)"
  fi
  if sta_is_ready; then
    ok "sta ($(command -v sta 2>/dev/null || echo "$VENV/bin/sta"))"
  else
    miss "sta   (built automatically in step 2 from OpenSTA + cudd)"
  fi
  if have openroad; then
    ok "openroad (native)"
  elif have docker && docker_do docker image inspect "$OPENLANE_IMAGE" >/dev/null 2>&1; then
    ok "openroad (via docker OpenLane image, for full place & route)"
  elif have docker; then
    warn "docker present but the OpenLane image is not pulled yet"
  else
    miss "openroad   (install docker for full place & route, or build natively)"
  fi

  step "PDK"
  if [ -d "$HOME/.volare/sky130A/libs.ref" ]; then
    ok "sky130A at ~/.volare/sky130A"
  else
    miss "sky130A   (pip install volare && volare enable --pdk sky130 $PDK_VERSION)"
  fi

  step "rtl2gdsagi"
  if [ -x "$VENV/bin/rtl2gdsagi" ]; then
    ok "installed  ($VENV/bin/rtl2gdsagi)"
  else
    miss "not installed yet"
  fi

  step "Claude API key"
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    ok "ANTHROPIC_API_KEY is set"
  else
    warn "ANTHROPIC_API_KEY not set — use --no-api, or export it to enable self-healing"
  fi
}

OPENLANE_IMAGE="ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69"
PDK_VERSION="bdc9412b3e468c102d01b7cf6337be06ec6e9c9a"

if [ "$CHECK_ONLY" = 1 ]; then
  report
  echo
  echo "Run without --check to install anything missing."
  exit 0
fi

# -------------------------------------------------------------- install ----

step "1/5  System packages"
MISSING=()
for t in verilator iverilog klayout git; do
  have "$t" || MISSING+=("$t")
done
# python3-venv provides the `venv` module; python3-pip provides pip3 for
# bootstrapping inside it. Both are frequently absent on minimal/fresh images.
python3 -c 'import venv' 2>/dev/null || MISSING+=(python3-venv)
have pip3 || MISSING+=(python3-pip)
if [ ${#MISSING[@]} -gt 0 ]; then
  echo "  installing: ${MISSING[*]}"
  sudo apt-get update -qq && sudo apt-get install -y "${MISSING[@]}" || \
    warn "apt-get failed; install these manually: ${MISSING[*]}"
else
  ok "already present"
fi

step "1a/5  CMake version"
if cmake_is_recent; then
  ok "cmake $(cmake_version) already satisfies >= $CMAKE_MIN_VERSION"
else
  if have cmake; then
    warn "apt/existing cmake ($(cmake_version)) is older than $CMAKE_MIN_VERSION — Yosys' build needs a newer one"
  else
    echo "  cmake not found"
  fi
  have snap || { echo "  snapd not found — installing it"; sudo apt-get update -qq && sudo apt-get install -y snapd; }
  if have snap; then
    echo "  installing latest cmake via snap (classic confinement)..."
    sudo snap install cmake --classic >/dev/null 2>&1
    hash -r
    if cmake_is_recent; then
      ok "cmake $(cmake_version) installed via snap"
    else
      warn "snap install of cmake failed or is still old — install manually: sudo snap install cmake --classic"
    fi
  else
    warn "no snapd available — install cmake >= $CMAKE_MIN_VERSION manually (snap is the recommended route on Ubuntu 22.04)"
  fi
fi

step "1b/5  Yosys (from source, CMake)"
if yosys_is_recent; then
  ok "yosys $(yosys_version) already satisfies >= $YOSYS_MIN_VERSION"
else
  if have yosys; then
    warn "apt/existing yosys ($(yosys_version)) is older than $YOSYS_MIN_VERSION — building from source"
  else
    echo "  yosys not found — building from source"
  fi
  if ! cmake_is_recent; then
    warn "cmake is still older than $CMAKE_MIN_VERSION — this build will likely fail (see step 1a above)"
  fi
  BUILD_DEPS=(build-essential cmake clang bison flex libreadline-dev gawk \
              tcl-dev libffi-dev git graphviz xdot pkg-config python3 \
              libboost-system-dev libboost-python-dev libboost-filesystem-dev \
              zlib1g-dev)
  MISSING_BUILD_DEPS=()
  for p in "${BUILD_DEPS[@]}"; do
    dpkg -s "$p" >/dev/null 2>&1 || MISSING_BUILD_DEPS+=("$p")
  done
  if [ ${#MISSING_BUILD_DEPS[@]} -gt 0 ]; then
    echo "  installing build deps: ${MISSING_BUILD_DEPS[*]}"
    sudo apt-get update -qq && sudo apt-get install -y "${MISSING_BUILD_DEPS[@]}" || \
      warn "apt-get failed to install some build deps; the cmake build below may fail"
  fi

  TMP="$(mktemp -d)"
  if git clone -q --recurse-submodules --depth 1 --branch "$YOSYS_GIT_REF" \
       https://github.com/YosysHQ/yosys.git "$TMP/yosys" 2>/dev/null; then
    (
      cd "$TMP/yosys" &&
      cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DYOSYS_ENABLE_UNIT_TESTS=OFF -DCMAKE_INSTALL_PREFIX="$VENV" >/dev/null &&
      cmake --build build -j"$(nproc)" >/dev/null &&
      cmake --install build >/dev/null
    ) && ok "yosys built and installed ($(yosys_version 2>/dev/null || echo new))" || \
      warn "yosys cmake build failed — check $TMP/yosys manually, or fall back to: sudo apt-get install yosys"
  else
    warn "could not clone YosysHQ/yosys (optional network issue) — yosys stays missing"
  fi
  rm -rf "$TMP"
fi

step "2/5  OpenSTA (via CUDD) and OpenROAD"
if sta_is_ready; then
  ok "sta already present ($(command -v sta 2>/dev/null || echo "$VENV/bin/sta"))"
else
  echo "  sta not found — building OpenSTA from source (needs CUDD for BDD support)"
  STA_BUILD_DEPS=(build-essential automake autoconf libtool \
                   tcl-dev swig bison flex libeigen3-dev libz-dev)
  MISSING_STA_DEPS=()
  for p in "${STA_BUILD_DEPS[@]}"; do
    dpkg -s "$p" >/dev/null 2>&1 || MISSING_STA_DEPS+=("$p")
  done
  if [ ${#MISSING_STA_DEPS[@]} -gt 0 ]; then
    echo "  installing build deps: ${MISSING_STA_DEPS[*]}"
    sudo apt-get update -qq && sudo apt-get install -y "${MISSING_STA_DEPS[@]}" || \
      warn "apt-get failed to install some build deps; the builds below may fail"
  fi

  if cudd_is_ready; then
    ok "cudd $CUDD_VERSION already built at $CUDD_PREFIX"
  else
    echo "  building cudd $CUDD_VERSION..."
    TMP="$(mktemp -d)"
    CUDD_LOG="/tmp/rtl2gdsagi-cudd-build.log"
    if git clone -q https://github.com/cuddorg/cudd.git "$TMP/cudd" 2>/dev/null; then
      if (
        cd "$TMP/cudd" &&
        git checkout -q "$CUDD_VERSION" &&
        # cudd's checked-in `configure` was generated with automake 1.14 and
        # hardcodes a call to `aclocal-1.14`, which doesn't exist once apt
        # gives you a newer automake (1.16+ on Ubuntu 22.04/24.04). Rebuilding
        # the autotools files with whatever aclocal/automake/libtool we
        # actually have avoids the "aclocal-1.14: command not found" error.
        { ! have autoreconf || autoreconf -fi; } &&
        ./configure --prefix="$CUDD_PREFIX" &&
        make -j"$(nproc)" &&
        make install
      ) >"$CUDD_LOG" 2>&1; then
        ok "cudd installed — note this path, OpenSTA needs it: $CUDD_PREFIX"
      else
        warn "cudd build failed (see $CUDD_LOG) — OpenSTA will be built without BDD support (slower conditional-arc handling)"
      fi
    else
      warn "could not clone cuddorg/cudd (optional network issue)"
    fi
    rm -rf "$TMP"
  fi

  echo "  building OpenSTA..."
  TMP="$(mktemp -d)"
  STA_LOG="/tmp/rtl2gdsagi-sta-build.log"
  if git clone -q --depth 1 https://github.com/The-OpenROAD-Project/OpenSTA.git "$TMP/OpenSTA" 2>/dev/null; then
    CUDD_ARG=()
    cudd_is_ready && CUDD_ARG=(-DCUDD_DIR="$CUDD_PREFIX")
    # BUILD_TESTS is ON by default and hard-requires `find_package(GTest REQUIRED)`.
    # Ubuntu's libgtest-dev package ships sources, not pre-built libs, so that
    # find_package fails on a fresh system — and we don't need STA's own test
    # suite for this flow, so just turn it off.
    if (
      mkdir -p "$TMP/OpenSTA/build" && cd "$TMP/OpenSTA/build" &&
      cmake "${CUDD_ARG[@]}" -DBUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX="$VENV" .. &&
      make -j"$(nproc)" &&
      make install
    ) >"$STA_LOG" 2>&1; then
      ok "sta built and installed ($VENV/bin/sta)"
    else
      warn "OpenSTA build failed (see $STA_LOG). Manual retry:
        git clone https://github.com/The-OpenROAD-Project/OpenSTA && cd OpenSTA && mkdir build && cd build &&
        cmake ${CUDD_ARG[*]:-} -DBUILD_TESTS=OFF .. && make -j\$(nproc) && sudo make install"
    fi
  else
    warn "could not clone The-OpenROAD-Project/OpenSTA (optional network issue)"
  fi
  rm -rf "$TMP"
fi

if have openroad; then
  ok "openroad already present (native)"
else
  if ! have docker; then
    echo "  docker not found — installing Docker Engine from Docker's official apt repository"
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    DOCKER_ARCH="$(dpkg --print-architecture)"
    # On Ubuntu derivatives (Linux Mint, etc.) VERSION_CODENAME is the
    # distro's own codename (e.g. "zena"), which Docker's repo has no suite
    # for — UBUNTU_CODENAME is the underlying Ubuntu base it actually needs.
    DOCKER_CODENAME="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}")"
    echo "deb [arch=$DOCKER_ARCH signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $DOCKER_CODENAME stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update -qq
    if sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
      ok "docker engine installed (docker-ce)"
    else
      warn "docker-ce install failed — falling back to Ubuntu's docker.io package"
      sudo apt-get install -y docker.io || warn "docker install failed — install manually and re-run"
    fi
    sudo systemctl enable --now docker >/dev/null 2>&1
  fi

  if have docker; then
    getent group docker >/dev/null 2>&1 || sudo groupadd docker
    # (checks the account's group list in /etc/group, not this shell's
    # active groups — that's what docker_do checks, further down)
    if id -nG "$USER" | tr ' ' '\n' | grep -qx docker; then
      ok "$USER already in the docker group"
    else
      echo "  adding $USER to the docker group"
      sudo usermod -aG docker "$USER"
      ok "added $USER to the docker group (using 'sg docker' below — no logout/login needed for this script)"
    fi

    if docker_do docker image inspect "$OPENLANE_IMAGE" >/dev/null 2>&1; then
      ok "OpenLane image already pulled (full place & route via docker)"
    else
      echo "  pulling the OpenLane image for full place & route (about 1 GB, one time)..."
      docker_do docker pull "$OPENLANE_IMAGE" >/dev/null 2>&1 && ok "pulled" || \
        warn "pull failed — check docker works with: sg docker -c 'docker run hello-world'"
    fi
  else
    warn "docker install did not succeed — install manually, e.g.: sudo apt-get install -y docker.io"
  fi
fi

step "3/5  Python environment"
if [ ! -x "$VENV/bin/pip" ]; then
  if ! python3 -m venv --upgrade-deps "$VENV" 2>/tmp/rtl2gdsagi-venv-err.log; then
    warn "venv creation failed (see /tmp/rtl2gdsagi-venv-err.log) — likely missing ensurepip; retrying after installing python3-venv/python3-pip"
    sudo apt-get update -qq && sudo apt-get install -y python3-venv python3-pip
    python3 -m venv --upgrade-deps "$VENV" || warn "venv creation still failing — try manually: python3 -m venv $VENV"
  fi
fi
if [ -x "$VENV/bin/pip" ]; then
  "$VENV/bin/pip" install -q --upgrade pip setuptools wheel
  "$VENV/bin/pip" install -q -e "$HERE" && ok "rtl2gdsagi installed" || \
    warn "install failed — try: $VENV/bin/pip install -e $HERE"
else
  warn "no working pip in $VENV — skipping rtl2gdsagi install (fix the venv above, then re-run)"
fi

step "4/5  SKY130 PDK"
if [ -d "$HOME/.volare/sky130A/libs.ref" ]; then
  ok "already installed"
elif [ ! -x "$VENV/bin/pip" ]; then
  warn "no working pip in $VENV — skipping PDK install (fix the venv above, then re-run)"
else
  echo "  installing (a few hundred MB, one time)..."
  "$VENV/bin/pip" install -q volare
  "$VENV/bin/volare" enable --pdk sky130 "$PDK_VERSION" >/dev/null 2>&1 && ok "sky130A ready" || \
    warn "volare failed — see https://github.com/efabless/volare"
fi

step "5/5  Formal equivalence (optional)"
if [ -x "$VENV/bin/sby" ] && [ -x "$VENV/bin/z3" ]; then
  ok "sby and z3 already in the venv"
elif [ ! -x "$VENV/bin/pip" ]; then
  warn "no working pip in $VENV — skipping z3 install (fix the venv above, then re-run)"
else
  Z3_LOG="/tmp/rtl2gdsagi-z3-install.log"
  if "$VENV/bin/pip" install -q click z3-solver >"$Z3_LOG" 2>&1; then
    ok "z3 installed"
  else
    warn "z3 install failed (see $Z3_LOG) — try: $VENV/bin/pip install click z3-solver"
  fi
  if [ ! -x "$VENV/bin/sby" ]; then
    TMP="$(mktemp -d)"
    if git clone -q --depth 1 https://github.com/YosysHQ/sby.git "$TMP/sby" 2>/dev/null; then
      (cd "$TMP/sby" && make install PREFIX="$VENV" >/dev/null 2>&1) && ok "sby installed" || \
        warn "sby build failed (optional — LEC uses a weaker strategy without it)"
    else
      warn "could not fetch sby (optional)"
    fi
    rm -rf "$TMP"
  fi
fi

if have eqy || [ -x "$VENV/bin/eqy" ]; then
  ok "eqy already installed"
else
  echo "  building eqy (needs the yosys built in step 1b — uses yosys-config)..."
  EQY_LOG="/tmp/rtl2gdsagi-eqy-build.log"
  TMP="$(mktemp -d)"
  if git clone -q --depth 1 https://github.com/YosysHQ/eqy.git "$TMP/eqy" 2>/dev/null; then
    if (cd "$TMP/eqy" && make PREFIX="$VENV" && make install PREFIX="$VENV") >"$EQY_LOG" 2>&1; then
      ok "eqy installed"
    else
      warn "eqy build failed (see $EQY_LOG; optional — formal equivalence signoff needs it). Manual retry:
      git clone https://github.com/YosysHQ/eqy && cd eqy && make && sudo make install"
    fi
  else
    warn "could not clone YosysHQ/eqy (optional network issue)"
  fi
  rm -rf "$TMP"
fi

echo
report

cat <<EOF

------------------------------------------------------------------
Ready. Try it:

  $VENV/bin/rtl2gdsagi doctor
  $VENV/bin/rtl2gdsagi run --rtl <your-rtl-dir> --top <your-top-module>

Add --no-api if you have not set ANTHROPIC_API_KEY.
Add --dry-run to generate every tool script without running anything.

Note: OpenSTA was built against cudd at $CUDD_PREFIX. If you ever rebuild
OpenSTA by hand, pass that path again with -DCUDD_DIR=$CUDD_PREFIX.

Note: if this run just added you to the docker group, plain "docker ..."
commands in THIS shell still won't see it until you log out and back in.
Use "sg docker -c 'docker ...'" (or open a new terminal) until then — new
shells after your next login won't need that.

Note: to run "rtl2gdsagi" (and yosys/sta/sby/eqy) from any directory
instead of typing the full $VENV/bin/... path, add this to the END of
~/.bashrc, then restart your shell (or run: source ~/.bashrc):

    export PATH="\$PATH:$VENV/bin"

Appending it (as above, not putting it first) is what makes this safe
despite $VENV/bin also containing python/python3/pip: PATH is searched
left-to-right, so your system's own python3/pip still win everywhere else
on this machine — only names PATH doesn't already resolve (rtl2gdsagi,
and yosys/sta/sby/eqy if you have no other copies) get picked up from
here. The one exception: if you'd separately apt-installed a yosys or
openroad before running this script, that older copy would still win
over the one built here when called bare — run "which yosys" to check.
------------------------------------------------------------------
EOF
