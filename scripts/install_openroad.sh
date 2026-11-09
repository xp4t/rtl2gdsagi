#!/usr/bin/env bash
# Standalone OpenROAD source installer; uses upstream's Bazel build.
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: ./install_openroad.sh [OPTIONS]

  --prefix DIR    Installation, source and logs (default: $HOME/eda/openroad)
  --ref REF       Upstream branch, tag or commit (default: master)
  --jobs N        Parallel build jobs (default: 4)
  --no-gui        Build only the command-line tool
  --skip-deps     Use dependencies already installed on this machine
  -h, --help      Show this help

Run as your normal user on Ubuntu 22.04/24.04/26.04, x86_64 or aarch64.
Requires internet and substantial free storage for source and Bazel downloads.
sudo installs system libraries; source, tools and OpenROAD stay under PREFIX.
Reruns fetch the requested revision and reuse build caches. Edited source trees
are rejected. No shell startup files are modified. SKY130 and OpenROAD-flow-
scripts are separate installations and are not included.
EOF
}
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '\n==> %s\n' "$*"; }

prefix="$HOME/eda/openroad"
ref=master
jobs=4
gui=yes
skip_deps=no
while (($#)); do
    case "$1" in
        --prefix|--ref|--jobs)
            (($# >= 2)) && [[ -n "$2" && "$2" != -* ]] || die "$1 needs a value."
            case "$1" in
                --prefix) prefix="$2" ;;
                --ref) ref="$2" ;;
                --jobs) jobs="$2" ;;
            esac
            shift 2 ;;
        --no-gui) gui=no; shift ;;
        --skip-deps) skip_deps=yes; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown argument: $1 (use --help)." ;;
    esac
done
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || die "--jobs must be a positive integer."
[[ "$EUID" -ne 0 ]] || die "Run as your normal user, without sudo."
[[ "$(uname -s)" == Linux && -r /etc/os-release ]] || die "Ubuntu Linux is required."
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu ]] || die "This installer targets Ubuntu."
case "${VERSION_ID:-}" in
    22.04|24.04|26.04) ;;
    *) die "Supported Ubuntu versions: 22.04, 24.04, 26.04." ;;
esac
case "$(uname -m)" in
    x86_64|aarch64) ;;
    *) die "Supported architectures: x86_64 and aarch64." ;;
esac
# Bazel workspace paths must not contain spaces; constrain paths before mkdir.
[[ "$prefix" =~ ^[a-zA-Z0-9_./-]+$ ]] || die "Use a prefix without spaces or shell characters."
mkdir -p -- "$prefix"
prefix="$(cd -- "$prefix" && pwd -P)"
[[ "$prefix" =~ ^/[a-zA-Z0-9_./-]+$ && "$prefix" != / ]] || die "Unsupported resolved prefix: $prefix"
repo="$prefix/src"
mkdir -p -- "$prefix/logs" "$prefix/tools/bin"
log_file="$prefix/logs/install-$(date +%Y%m%d-%H%M%S)-$$.log"
exec > >(tee -a "$log_file") 2>&1
trap 'printf "\nInstallation failed at line %s. Log: %s\n" "$LINENO" "$log_file" >&2' ERR

if [[ "$skip_deps" == no ]]; then
    command -v sudo >/dev/null || die "sudo is required to install system dependencies."
    missing=()
    for package in ca-certificates curl git; do
        if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != 'install ok installed' ]]; then
            missing+=("$package")
        fi
    done
    if ((${#missing[@]})); then
        log "Installing download tools"
        sudo apt-get update
        sudo apt-get install -y "${missing[@]}"
    fi
fi
command -v git >/dev/null || die "git is missing; rerun without --skip-deps."

log "Fetching OpenROAD revision: $ref"
upstream=https://github.com/The-OpenROAD-Project/OpenROAD.git
if [[ ! -e "$repo" ]]; then
    git init "$repo"
    git -C "$repo" remote add origin "$upstream"
fi
[[ -d "$repo/.git" ]] || die "$repo is not a Git checkout; choose another --prefix."
[[ "$(git -C "$repo" remote get-url origin)" == "$upstream" ]] || die "Unexpected source origin in $repo."
[[ -z "$(git -C "$repo" status --porcelain)" ]] || die "Source tree has local changes. Preserve them or choose another --prefix."
git -C "$repo" fetch --depth 1 origin "$ref"
git -C "$repo" checkout --detach FETCH_HEAD
git -C "$repo" submodule sync --recursive
git -C "$repo" submodule update --init --recursive --depth 1
commit="$(git -C "$repo" rev-parse HEAD)"
log "Source commit: $commit"
[[ -f "$repo/MODULE.bazel" && -f "$repo/etc/Build.sh" ]] || die "Selected revision does not provide the supported Bazel build."

export PATH="$prefix/tools/bin:$PATH"
cd -- "$repo"
dependency_args=()
build_args=("-prefix=$prefix" "-threads=$jobs")
if [[ "$gui" == no ]]; then
    dependency_args+=(-no-gui)
    build_args+=(-no-gui)
fi
if [[ "$skip_deps" == no ]]; then
    log "Installing system libraries using OpenROAD's dependency installer"
    sudo bash ./etc/DependencyInstaller.sh -base "${dependency_args[@]}"
    log "Installing Bazelisk under $prefix/tools if needed"
    bash ./etc/DependencyInstaller.sh -common "-prefix=$prefix/tools" "${dependency_args[@]}"
fi
command -v bazelisk >/dev/null || command -v bazel >/dev/null || die "Bazelisk is missing; rerun without --skip-deps."
log "Building and installing OpenROAD ($jobs jobs, GUI: $gui)"
bash ./etc/Build.sh "${build_args[@]}"

log "Checking installed binary and Tcl/OpenDB initialization"
[[ -x "$prefix/bin/openroad" ]] || die "Build finished without installing bin/openroad."
"$prefix/bin/openroad" -version
smoke_script="$prefix/logs/smoke-$$.tcl"
cat > "$smoke_script" <<'EOF'
set db [ord::get_db]
if {$db eq "NULL" || $db eq ""} {
    error "OpenDB database was not initialized"
}
puts "OPENROAD_INSTALL_SMOKE_OK"
exit
EOF
smoke_output="$("$prefix/bin/openroad" -no_init -exit "$smoke_script" 2>&1)"
printf '%s\n' "$smoke_output"
[[ "$smoke_output" == *OPENROAD_INSTALL_SMOKE_OK* ]] || die "OpenROAD smoke check failed."

{
    printf '# Source this file in Bash to use standalone OpenROAD.\n'
    printf 'export PATH=%q:"$PATH"\n' "$prefix/bin"
} > "$prefix/env.sh"
printf '%s\n' "$commit" > "$prefix/installed-commit.txt"
log "OpenROAD installed successfully"
printf 'In each new terminal, run:\n  source %q\n  openroad -version\n' "$prefix/env.sh"
if [[ "$gui" == yes ]]; then printf 'Launch the GUI with: openroad -gui\n'; fi
printf 'Installation log: %s\n' "$log_file"
