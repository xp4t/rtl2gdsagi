#!/usr/bin/env bash
# OpenLane 1 (flow.tcl) + SKY130A; refresh only OpenLane 1 Docker images.
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: ./install_openlane1_sky130.sh [--prefix DIR] [--pdk-root DIR]

Default installation: $HOME/eda/openlane1
Default PDK root:     PREFIX/pdks

Uses upstream's supported OpenLane 1 "superstable" branch. On every run:
  1. Fetch its current source revision (preserving user design files).
  2. Remove cached OpenLane 1 images and their aliases.
  3. Pull the matching official image, install SKY130A and run make test.

Recognized image repositories: ghcr.io/the-openroad-project/openlane,
efabless/openlane, docker.io/efabless/openlane, gds-studio/openlane, openlane.
All tags sharing a recognized image ID are removed, including custom aliases.
Containers are never deleted; images used by containers block cleanup.
OpenLane 2 images, unrelated images, volumes and shared PDKs are not removed.

Run as your normal user. sudo is used for missing dependencies and Docker
access if necessary. Installation needs several GB of storage and internet.
Paths must use letters, digits, underscores, dots, slashes or hyphens because
OpenLane 1's upstream Makefile does not safely support other path characters.
EOF
}
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '\n==> %s\n' "$*"; }
prefix="$HOME/eda/openlane1"
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
[[ "$EUID" -ne 0 ]] || die "Run as your normal user, without sudo."
[[ "$(uname -s)" == Linux && -r /etc/os-release ]] || die "Ubuntu/Debian Linux is required."
# shellcheck disable=SC1091
source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
    *ubuntu*|*debian*) ;;
    *) die "Ubuntu/Debian Linux is required." ;;
esac
case "$(uname -m)" in
    x86_64) arch=amd64 ;;
    aarch64) arch=arm64 ;;
    *) die "Supported architectures: x86_64 and aarch64." ;;
esac
command -v sudo >/dev/null || die "sudo is required."
for path in "$HOME" "$prefix" "${pdk_root:-$prefix/pdks}"; do
    [[ "$path" =~ ^[a-zA-Z0-9_./-]+$ ]] || die "Unsupported characters in path: $path"
done
mkdir -p -- "$prefix"
prefix="$(cd -- "$prefix" && pwd -P)"
pdk_root="${pdk_root:-$prefix/pdks}"
mkdir -p -- "$pdk_root" "$prefix/bin" "$prefix/docker-bin"
pdk_root="$(cd -- "$pdk_root" && pwd -P)"
for path in "$prefix" "$pdk_root"; do
    [[ "$path" =~ ^/[a-zA-Z0-9_./-]+$ ]] || die "Unsupported resolved path: $path"
done
repo="$prefix/src"
exec > >(tee -a "$prefix/install.log") 2>&1
trap 'printf "\nInstallation failed at line %s. See %s/install.log.\n" "$LINENO" "$prefix" >&2' ERR

log "Installing missing Ubuntu/Debian dependencies"
missing=()
for package in ca-certificates curl git make python3 python3-pip python3-venv; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != 'install ok installed' ]]; then
        missing+=("$package")
    fi
done
if ! command -v docker >/dev/null; then missing+=(docker.io); fi
if ((${#missing[@]})); then
    sudo apt-get update
    sudo apt-get install -y "${missing[@]}"
fi
docker_binary="$(command -v docker)"
docker_runner=("$docker_binary")
if ! "${docker_runner[@]}" info >/dev/null 2>&1; then
    # Check privileges before trying to start a daemon. Only use sudo for
    # Docker's default local context; preserve remote/rootless contexts.
    if [[ -z "${DOCKER_HOST:-}" && -z "${DOCKER_CONTEXT:-}" ]] \
        && [[ "$("$docker_binary" context show)" == default ]]; then
        if sudo "$docker_binary" info >/dev/null 2>&1; then
            docker_runner=(sudo "$docker_binary")
        else
            if command -v systemctl >/dev/null; then
                sudo systemctl start docker.service
            fi
            if "${docker_runner[@]}" info >/dev/null 2>&1; then
                :
            elif sudo "$docker_binary" info >/dev/null 2>&1; then
                docker_runner=(sudo "$docker_binary")
            else
                die "Cannot access Docker. Start Docker/fix its permissions, then rerun."
            fi
        fi
    else
        die "Cannot access the selected Docker context. Start Docker/fix its permissions, then rerun."
    fi
fi

# Make calls Docker by name. Scope this wrapper to this installation's
# launcher/Make invocations instead of changing system Docker permissions.
{
    printf '#!/usr/bin/env bash\nexec '
    printf '%q ' "${docker_runner[@]}"
    printf '"$@"\n'
} > "$prefix/docker-bin/docker"
chmod +x "$prefix/docker-bin/docker"

log "Fetching the supported OpenLane 1 source (superstable)"
upstream=https://github.com/The-OpenROAD-Project/OpenLane.git
if [[ ! -e "$repo" ]]; then
    git clone --depth 1 --branch superstable "$upstream" "$repo"
fi
[[ -d "$repo/.git" ]] || die "$repo is not an OpenLane Git checkout. Use another --prefix."
[[ "$(git -C "$repo" remote get-url origin)" == "$upstream" ]] || die "Unexpected origin in $repo. Use another --prefix."
[[ -z "$(git -C "$repo" status --porcelain --untracked-files=no)" ]] || die "Tracked files in $repo were edited. Commit/stash them or use another --prefix."
git -C "$repo" fetch --depth 1 origin superstable
git -C "$repo" checkout --detach FETCH_HEAD
commit="$(git -C "$repo" rev-parse HEAD)"
image="ghcr.io/the-openroad-project/openlane:$commit"
log "Required Docker image: $image (linux/$arch)"

log "Finding cached OpenLane 1 images"
listing="$("${docker_runner[@]}" image ls --no-trunc --format '{{.Repository}} {{.Tag}} {{.ID}}')"
declare -A old_images=()
while read -r repository tag image_id; do
    case "$repository" in
        ghcr.io/the-openroad-project/openlane|efabless/openlane|docker.io/efabless/openlane|gds-studio/openlane|openlane)
            old_images["$image_id"]=1 ;;
    esac
done <<< "$listing"

# Check every existing container before removing any tag. Stopped containers
# may contain work too; do not delete or force-remove their images.
if ((${#old_images[@]})); then
    container_list="$("${docker_runner[@]}" ps -aq)"
    containers=()
    while read -r container_id; do
        [[ -z "$container_id" ]] || containers+=("$container_id")
    done <<< "$container_list"
    if ((${#containers[@]})); then
        container_info="$("${docker_runner[@]}" inspect --format '{{.Id}} {{.Image}} {{.Name}}' "${containers[@]}")"
        blocked=0
        while read -r container_id image_id container_name; do
            if [[ -n "${old_images[$image_id]:-}" ]]; then
                printf 'Container %s (%s) uses OpenLane 1 image %s\n' "$container_name" "$container_id" "$image_id"
                blocked=1
            fi
        done <<< "$container_info"
        ((blocked == 0)) || die "Cleanup blocked by the listed containers. Preserve their work and remove those containers yourself, then rerun."
    fi
    log "Removing cached OpenLane 1 image tags, including aliases"
    while read -r repository tag image_id; do
        if [[ -n "$image_id" && -n "${old_images[$image_id]:-}" && "$repository" != '<none>' && "$tag" != '<none>' ]]; then
            "${docker_runner[@]}" image rm "$repository:$tag"
        fi
    done <<< "$listing"
    for image_id in "${!old_images[@]}"; do
        if "${docker_runner[@]}" image inspect "$image_id" >/dev/null 2>&1; then
            "${docker_runner[@]}" image rm "$image_id"
        fi
    done
else
    log "No cached OpenLane 1 images found"
fi

log "Pulling the matching official OpenLane 1 image from the registry"
"${docker_runner[@]}" pull --platform "linux/$arch" "$image"
# OpenLane 1's Makefile appends an architecture suffix when running Docker.
"${docker_runner[@]}" tag "$image" "$image-$arch"
"${docker_runner[@]}" image inspect "$image" --format 'Installed image: {{.Id}}; registry digests: {{json .RepoDigests}}'

# Explicit Make variables isolate this setup from OpenLane 2 shell settings.
make_args=("PDK_ROOT=$pdk_root" PDK=sky130A STD_CELL_LIBRARY=sky130_fd_sc_hd
    "OPENLANE_IMAGE_NAME=$image" "DOCKER_ARCH=$arch" PYTHON_BIN=python3)
log "Installing the matching SKY130A PDK"
env -u PYTHONHOME PYTHONPATH= PYTHONNOUSERSITE=1 PATH="$prefix/docker-bin:$PATH" \
    make -C "$repo" "${make_args[@]}" pdk
[[ -d "$pdk_root/sky130A/libs.ref" && -d "$pdk_root/sky130A/libs.tech" ]] \
    || die "SKY130A was not enabled under $pdk_root. Check the PDK installation log."

log "Running OpenLane 1's spm RTL-to-GDS test"
test_log="$prefix/test-$(date +%Y%m%d-%H%M%S)-$$.log"
env -u PYTHONHOME PYTHONPATH= PYTHONNOUSERSITE=1 PATH="$prefix/docker-bin:$PATH" \
    make -C "$repo" "${make_args[@]}" test | tee "$test_log"
# Upstream's Makefile can print 'Basic test failed' yet return zero.
grep -Fxq 'Basic test passed' "$test_log" || die "OpenLane 1's test did not report success. See $test_log."
[[ -s "$repo/designs/spm/runs/openlane_test/results/signoff/spm.gds" ]] \
    || die "The test did not produce the expected GDS file. See $test_log."

log "Creating the OpenLane 1 tool-shell launcher"
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\n'
    printf 'cd %q\n' "$repo"
    printf 'exec env -u PYTHONHOME PYTHONPATH= PYTHONNOUSERSITE=1 PATH=%q:"$PATH" make ' "$prefix/docker-bin"
    printf '%q ' "${make_args[@]}" mount
    printf '\n'
} > "$prefix/bin/openlane1-shell"
chmod +x "$prefix/bin/openlane1-shell"
printf 'export PATH=%q:"$PATH"\n' "$prefix/bin" > "$prefix/env.sh"

log "OpenLane 1 + SKY130A installed; Basic test passed"
printf 'Source revision: %s\nPDK: %s/sky130A\nLog: %s/install.log\n\n' "$commit" "$pdk_root" "$prefix"
printf 'Enter the tool environment:\n  %q\n\nInside it, run:\n  ./flow.tcl -design spm\n' "$prefix/bin/openlane1-shell"
