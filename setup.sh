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
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
miss() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

# --------------------------------------------------------------- report ----

report() {
  step "Tools"
  for t in verilator iverilog yosys klayout; do
    have "$t" && ok "$t" || miss "$t   (apt-get install $t)"
  done
  have eqy && ok "eqy" || warn "eqy   (optional: formal equivalence; signoff needs it)"
  [ -x "$VENV/bin/sby" ] && ok "sby (in venv)" || warn "sby   (optional: stronger equivalence proofs)"
  [ -x "$VENV/bin/z3" ]  && ok "z3 (in venv)"  || warn "z3    (optional: SMT solver for sby)"

  if have openroad && have sta; then
    ok "openroad + sta (native)"
  elif have docker; then
    if docker image inspect "$OPENLANE_IMAGE" >/dev/null 2>&1; then
      ok "openroad + sta (via docker image)"
    else
      warn "docker present but the OpenLane image is not pulled yet"
    fi
  else
    miss "openroad/sta   (install docker, or build them natively)"
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
for t in verilator iverilog yosys klayout git; do
  have "$t" || MISSING+=("$t")
done
python3 -c 'import venv' 2>/dev/null || MISSING+=(python3-venv)
if [ ${#MISSING[@]} -gt 0 ]; then
  echo "  installing: ${MISSING[*]}"
  sudo apt-get update -qq && sudo apt-get install -y "${MISSING[@]}" || \
    warn "apt-get failed; install these manually: ${MISSING[*]}"
else
  ok "already present"
fi

step "2/5  OpenROAD and OpenSTA"
if have openroad && have sta; then
  ok "native install found"
elif have docker; then
  if docker image inspect "$OPENLANE_IMAGE" >/dev/null 2>&1; then
    ok "OpenLane image already pulled"
  else
    echo "  pulling the OpenLane image (about 1 GB, one time)..."
    docker pull "$OPENLANE_IMAGE" >/dev/null 2>&1 && ok "pulled" || \
      warn "pull failed — check 'docker run hello-world' works for your user"
  fi
else
  warn "no docker and no native openroad. Install docker:"
  echo "      sudo apt-get install -y docker.io"
  echo "      sudo usermod -aG docker \$USER   # then log out and back in"
fi

step "3/5  Python environment"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -e "$HERE" && ok "rtl2gdsagi installed" || \
  warn "install failed — try: $VENV/bin/pip install -e $HERE"

step "4/5  SKY130 PDK"
if [ -d "$HOME/.volare/sky130A/libs.ref" ]; then
  ok "already installed"
else
  echo "  installing (a few hundred MB, one time)..."
  "$VENV/bin/pip" install -q volare
  "$VENV/bin/volare" enable --pdk sky130 "$PDK_VERSION" >/dev/null 2>&1 && ok "sky130A ready" || \
    warn "volare failed — see https://github.com/efabless/volare"
fi

step "5/5  Formal equivalence (optional)"
if [ -x "$VENV/bin/sby" ] && [ -x "$VENV/bin/z3" ]; then
  ok "sby and z3 already in the venv"
else
  "$VENV/bin/pip" install -q click z3-solver && ok "z3 installed"
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
have eqy || warn "eqy not found (optional but recommended):
      git clone https://github.com/YosysHQ/eqy && cd eqy && make && sudo make install"

echo
report

cat <<EOF

------------------------------------------------------------------
Ready. Try it:

  $VENV/bin/rtl2gdsagi doctor
  $VENV/bin/rtl2gdsagi run --rtl <your-rtl-dir> --top <your-top-module>

Add --no-api if you have not set ANTHROPIC_API_KEY.
Add --dry-run to generate every tool script without running anything.
------------------------------------------------------------------
EOF
