#!/usr/bin/env bash
# ============================================================
# SCRIPT CREATED FOR CHIPCRAFT BOOTCAMP, ./setup.sh inside the rtl2gdsagi folder handles all these, if you are not a student of CHIPCRAFT bootcamp then ignore this.
# OpenSTA + CUDD Installation Script
# Ubuntu / Debian
# CUDD Version : 3.0.0
# OpenSTA      : Latest source from GitHub
# Usage:
#   chmod +x installsta.sh
#   ./installsta.sh
# ============================================================

set -Eeuo pipefail

CUDD_VERSION="3.0.0"

INSTALL_PREFIX="/usr/local"
CUDD_PREFIX="$INSTALL_PREFIX"

BUILD_ROOT="$HOME/sta_build"
CUDD_DIR="$BUILD_ROOT/cudd"
STA_DIR="$BUILD_ROOT/OpenSTA"

JOBS="$(nproc)"

LOG_DIR="$BUILD_ROOT/logs"
mkdir -p "$BUILD_ROOT" "$LOG_DIR"

CUDD_LOG="$LOG_DIR/cudd.log"
STA_LOG="$LOG_DIR/opensta.log"

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
step() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

success() { echo "[SUCCESS] $1"; }
error()   { echo "[ERROR] $1" >&2; }

# ------------------------------------------------------------
# Error handling
# ------------------------------------------------------------
trap 'error "Installation failed at line $LINENO. Check logs in $LOG_DIR"' ERR

# ------------------------------------------------------------
# 1. Install dependencies
# ------------------------------------------------------------
step "1. Installing system dependencies"

sudo apt-get update
sudo apt-get install -y \
    build-essential \
    ca-certificates \
    git \
    cmake \
    automake \
    autoconf \
    libtool \
    m4 \
    perl \
    bison \
    flex \
    swig \
    tcl-dev \
    tcl8.6-dev \
    libeigen3-dev \
    zlib1g-dev \
    pkg-config

sudo apt-get install -y --reinstall "linux-headers-$(uname -r)"

sudo apt-get install -y --reinstall \
    linux-headers-7.0.0-38-generic \
    linux-headers-generic

success "System dependencies installed"

# ------------------------------------------------------------
# 2. Download CUDD
# ------------------------------------------------------------
step "2. Downloading CUDD $CUDD_VERSION"

if [ ! -d "$CUDD_DIR/.git" ]; then
    git clone https://github.com/cuddorg/cudd.git "$CUDD_DIR"
else
    echo "CUDD repository already exists"
fi

cd "$CUDD_DIR"
git fetch --tags
git checkout "$CUDD_VERSION"

# ------------------------------------------------------------
# 3. Configure and compile CUDD
# ------------------------------------------------------------
step "3. Building CUDD"

# Regenerate Autotools files to avoid the old aclocal-1.14 dependency.
autoreconf -fi 2>&1 | tee "$CUDD_LOG"

./configure --prefix="$CUDD_PREFIX" 2>&1 | tee -a "$CUDD_LOG"

make -j"$JOBS" 2>&1 | tee -a "$CUDD_LOG"

# ------------------------------------------------------------
# 4. Install CUDD
# ------------------------------------------------------------
step "4. Installing CUDD"

sudo make install 2>&1 | tee -a "$CUDD_LOG"
sudo ldconfig

if [ ! -f "$INSTALL_PREFIX/include/cudd.h" ]; then
    error "CUDD header not found"
    exit 1
fi

if [ ! -f "$INSTALL_PREFIX/lib/libcudd.a" ]; then
    error "CUDD library not found"
    exit 1
fi

success "CUDD installed successfully"

# ------------------------------------------------------------
# 5. Download OpenSTA
# ------------------------------------------------------------
step "5. Downloading OpenSTA"

if [ ! -d "$STA_DIR/.git" ]; then
    git clone https://github.com/The-OpenROAD-Project/OpenSTA.git "$STA_DIR"
else
    echo "OpenSTA repository already exists"
    git -C "$STA_DIR" pull --ff-only
fi

# ------------------------------------------------------------
# 6. Configure OpenSTA
# ------------------------------------------------------------
step "6. Configuring OpenSTA"

mkdir -p "$STA_DIR/build"
cd "$STA_DIR/build"

cmake \
    -DCUDD_DIR="$CUDD_PREFIX" \
    -DBUILD_TESTS=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    .. 2>&1 | tee "$STA_LOG"

# ------------------------------------------------------------
# 7. Compile OpenSTA
# ------------------------------------------------------------
step "7. Compiling OpenSTA"

make -j"$JOBS" 2>&1 | tee -a "$STA_LOG"

success "OpenSTA compilation completed"

# ------------------------------------------------------------
# 8. Install OpenSTA
# ------------------------------------------------------------
step "8. Installing OpenSTA"

sudo make install 2>&1 | tee -a "$STA_LOG"
sudo ldconfig

# ------------------------------------------------------------
# 9. Verify installation
# ------------------------------------------------------------
step "9. Verifying installation"

if command -v sta >/dev/null 2>&1; then
    success "OpenSTA executable found: $(command -v sta)"
    sta -version || true
else
    error "OpenSTA executable not found in PATH"
    echo "Check the installation directory:"
    echo "$INSTALL_PREFIX/bin"
    exit 1
fi

# Check CUDD
if [ -f "$INSTALL_PREFIX/lib/libcudd.a" ]; then
    success "CUDD library found"
else
    error "CUDD library missing"
    exit 1
fi

# ------------------------------------------------------------
# 10. Final report
# ------------------------------------------------------------
step "INSTALLATION COMPLETED"

echo
echo "CUDD installation:"
echo "  Header : $INSTALL_PREFIX/include/cudd.h"
echo "  Library: $INSTALL_PREFIX/lib/libcudd.a"

echo
echo "OpenSTA installation:"
echo "  Binary : $(command -v sta)"

echo
echo "Build directories:"
echo "  CUDD   : $CUDD_DIR"
echo "  OpenSTA: $STA_DIR"

echo
echo "Logs:"
echo "  CUDD   : $CUDD_LOG"
echo "  OpenSTA: $STA_LOG"

echo
echo "To launch OpenSTA:"
echo
echo "  sta"
echo
echo "To check version:"
echo
echo "  sta -version"
echo

success "All installations completed successfully!"
