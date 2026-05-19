#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# add_swap.sh — provision a swap file on a Lightsail (or any Ubuntu) host.
#
# The 1 GB Lightsail tier ships with no swap. Under memory pressure (apt
# unattended-upgrades, snapd refresh, log rotation, …) the kernel can stall
# before the OOM killer reclaims memory, which manifests as AWS status check
# failures with low CPU. A small swap file turns these hangs into graceful
# slowdowns.
#
# The script is idempotent: re-running it is a no-op once swap is active.
#
# Usage:
#   ./scripts/add_swap.sh           # default 2 GB
#   SWAP_SIZE_GB=4 ./scripts/add_swap.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SWAP_FILE="${SWAP_FILE:-/swapfile}"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-2}"
SWAPPINESS="${SWAPPINESS:-10}"

if [ -n "$(sudo swapon --show --noheadings)" ]; then
    echo "Swap is already active:"
    sudo swapon --show
    exit 0
fi

if [ -e "$SWAP_FILE" ]; then
    echo "Error: $SWAP_FILE already exists but is not active. Inspect and remove it before re-running." >&2
    exit 1
fi

echo "Allocating ${SWAP_SIZE_GB} GB at ${SWAP_FILE}..."
if ! sudo fallocate -l "${SWAP_SIZE_GB}G" "$SWAP_FILE" 2>/dev/null; then
    echo "fallocate unsupported on this filesystem, falling back to dd..."
    sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count=$((SWAP_SIZE_GB * 1024)) status=progress
fi

sudo chmod 600 "$SWAP_FILE"
sudo mkswap "$SWAP_FILE"
sudo swapon "$SWAP_FILE"

if ! grep -qE "^${SWAP_FILE}[[:space:]]" /etc/fstab; then
    echo "${SWAP_FILE} none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
    echo "Added ${SWAP_FILE} to /etc/fstab."
fi

SYSCTL_CONF=/etc/sysctl.d/99-einki-swappiness.conf
if [ ! -f "$SYSCTL_CONF" ]; then
    echo "vm.swappiness=${SWAPPINESS}" | sudo tee "$SYSCTL_CONF" >/dev/null
    sudo sysctl --system >/dev/null
    echo "Set vm.swappiness=${SWAPPINESS} (persisted in ${SYSCTL_CONF})."
fi

echo ""
echo "Done. Current memory + swap:"
free -h
