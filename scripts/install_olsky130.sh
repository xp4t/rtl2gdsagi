#!/usr/bin/env bash
# Install OpenLane 2 and its matching, prebuilt SKY130A PDK on Ubuntu/Debian.
# References:
# https://openlane2.readthedocs.io/en/latest/getting_started/common/nix_installation/installation_linux.html
# https://openlane2.readthedocs.io/en/latest/getting_started/migrants/index.html
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: ./install_openlane_sky130.sh [--prefix DIR] [--pdk-root DIR]

  --prefix DIR    Install under DIR (default: $HOME/eda/openlane2).
  --pdk-root DIR  Store the PDK in DIR (default: PREFIX/pdks).
  -h, --help     Show this help without changing the system.

Run as your normal user, without sudo. The script uses sudo for missing
APT dependencies, Nix installation and Nix's system binary-cache settings.
It downloads the EDA tools and SKY130A, then runs OpenLane's smoke test.
Downloads require several GB and can take a while. Rerun after a failure.
EOF
}

die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '\n==> %s\n' "$*"; }

prefix="${HOME}/eda/openlane2"
pdk_root=""
while (($#)); do
    case "$1" in
        --prefix|--pdk-root)
            (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || die "$1 needs a directory."
            if [[ "$1" == --prefix ]]; then prefix="$2"; else pdk_root="$2"; fi
            shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown argument: $1 (use --help)." ;;
    esac
done

[[ "$EUID" -ne 0 ]] || die "Run this script as your normal user, without sudo."
[[ "$(uname -s)" == Linux ]] || die "This installer supports Ubuntu/Debian Linux."
[[ -r /etc/os-release ]] || die "Cannot detect the Linux distribution."
# shellcheck disable=SC1091
source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
    *ubuntu*|*debian*) ;;
    *) die "This installer supports Ubuntu/Debian; detected ${PRETTY_NAME:-unknown}." ;;
esac
case "$(uname -m)" in
    x86_64|aarch64) ;;
    *) die "OpenLane's prebuilt tools require x86_64 or aarch64." ;;
esac
command -v sudo >/dev/null || die "sudo is required for system dependencies."

mkdir -p -- "$prefix"
prefix="$(cd -- "$prefix" && pwd -P)"
pdk_root="${pdk_root:-$prefix/pdks}"
mkdir -p -- "$pdk_root" "$prefix/bin"
pdk_root="$(cd -- "$pdk_root" && pwd -P)"
repo="$prefix/src"
exec > >(tee -a "$prefix/install.log") 2>&1
installer=""
trap '[[ -z "$installer" ]] || rm -f -- "$installer"' EXIT
trap 'printf "\nInstallation failed at line %s. See %s/install.log and rerun after fixing the error.\n" "$LINENO" "$prefix" >&2' ERR

log "Installing missing host dependencies"
missing=()
for package in ca-certificates curl git xz-utils; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != 'install ok installed' ]]; then
        missing+=("$package")
    fi
done
if ((${#missing[@]})); then
    sudo apt-get update
    sudo apt-get install -y "${missing[@]}"
fi

load_nix() {
    # Nix may already be installed but absent from this terminal's PATH.
    local profile
    for profile in /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh "$HOME/.nix-profile/etc/profile.d/nix.sh"; do
        if [[ -r "$profile" ]]; then
            # Installer-provided profiles may reference unset shell variables.
            set +u
            # shellcheck disable=SC1090
            source "$profile"
            set -u
            break
        fi
    done
}
load_nix
cache='extra-substituters = https://openlane.cachix.org'
cache_key='extra-trusted-public-keys = openlane.cachix.org-1:qqdwh+QMNGmZAuyeQJTH9ErW57OWSvdtuwfBKdS254E='
if ! command -v nix-shell >/dev/null; then
    [[ ! -e /nix/nix-installer ]] || die "An existing Nix installation needs repair; load its profile before rerunning."
    log "Installing Nix and enabling OpenLane's binary cache"
    installer="$(mktemp)"
    curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL --retry 3 \
        https://install.determinate.systems/nix -o "$installer"
    sh "$installer" install --no-confirm --extra-conf "$cache
$cache_key"
    load_nix
else
    log "Checking OpenLane's binary cache for the existing Nix installation"
    changed=0
    for setting in "$cache" "$cache_key"; do
        if ! grep -Fqx -- "$setting" /etc/nix/nix.conf 2>/dev/null; then
            sudo mkdir -p /etc/nix
            printf '\n%s\n' "$setting" | sudo tee -a /etc/nix/nix.conf >/dev/null
            changed=1
        fi
    done
    if ((changed)); then
        if command -v systemctl >/dev/null && systemctl is-active --quiet nix-daemon.service; then
            sudo systemctl restart nix-daemon.service
        elif command -v pgrep >/dev/null && pgrep -x nix-daemon >/dev/null; then
            # As in OpenLane's guide: the socket/launch mechanism restarts it.
            sudo pkill -x nix-daemon
        fi
    fi
fi
command -v nix-shell >/dev/null || die "Nix installed but nix-shell is unavailable. Open a new terminal and rerun."
nix_shell="$(command -v nix-shell)"

# Pin a published OpenLane release and verify its commit on first install/rerun.
version='2.3.10'
commit='b89f7866fd3d19da470220baf89d0e7804962941'
log "Downloading OpenLane $version"
if [[ ! -e "$repo" ]]; then
    git clone --depth 1 --branch "$version" https://github.com/chipfoundry/openlane2.git "$repo"
fi
[[ -d "$repo/.git" ]] || die "$repo exists but is not an OpenLane checkout. Use another --prefix."
[[ "$(git -C "$repo" rev-parse HEAD)" == "$commit" ]] || die "$repo has a different revision. Use another --prefix."
[[ -z "$(git -C "$repo" status --porcelain)" ]] || die "$repo contains local changes. Use another --prefix or review those changes first."
[[ -f "$repo/shell.nix" ]] || die "Missing OpenLane shell.nix."

# %q preserves spaces and shell metacharacters in installation paths/arguments.
log "Creating launchers and environment file"
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\n'
    printf 'export PDK_ROOT=%q\nexport PDK=sky130A\n' "$pdk_root"
    printf 'printf -v command_line "%%q " openlane "$@"\n'
    printf 'exec %q %q --run "$command_line"\n' "$nix_shell" "$repo/shell.nix"
} > "$prefix/bin/openlane"
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\n'
    printf 'export PDK_ROOT=%q\nexport PDK=sky130A\n' "$pdk_root"
    printf 'exec %q %q "$@"\n' "$nix_shell" "$repo/shell.nix"
} > "$prefix/bin/openlane-shell"
chmod +x "$prefix/bin/openlane" "$prefix/bin/openlane-shell"
{
    printf '# Source this file to use OpenLane from your terminal.\n'
    printf 'export PATH=%q:"$PATH"\n' "$prefix/bin"
    printf 'export PDK_ROOT=%q\nexport PDK=sky130A\n' "$pdk_root"
} > "$prefix/env.sh"

log "Downloading the toolchain and SKY130A; running the OpenLane smoke test"
# OpenLane uses Volare to fetch the PDK revision matched to this release.
# A shell alone does not fetch the PDK; running the flow is necessary.
"$prefix/bin/openlane" --pdk-root "$pdk_root" --pdk sky130A --smoke-test
# OpenLane fetches a version without enabling Volare's top-level sky130A
# shortcut. Resolve the same revision as OpenLane instead of requiring it.
printf -v resolve_command '%q ' python3 -c \
    'import os, sys, volare; from openlane.common import get_opdks_rev; print(os.path.join(volare.Version(name=get_opdks_rev(), pdk="sky130").get_dir(sys.argv[1]), "sky130A"))' \
    "$pdk_root"
pdk_path="$("$nix_shell" "$repo/shell.nix" --run "$resolve_command")"
[[ -d "$pdk_path/libs.ref" && -d "$pdk_path/libs.tech" ]] \
    || die "The smoke test returned, but SKY130A is missing from $pdk_path."

log "OpenLane $version and SKY130A installed; smoke test passed"
printf '\nStart using it:\n  source %q\n  openlane --run-example spm\n\n' "$prefix/env.sh"
printf 'For a shell with Yosys, OpenROAD, Magic, Netgen and KLayout:\n  %q\n\n' "$prefix/bin/openlane-shell"
printf 'PDK location: %s\nLog: %s/install.log\n' "$pdk_path" "$prefix"
