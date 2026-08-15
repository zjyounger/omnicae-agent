#!/usr/bin/env bash
set -euo pipefail

readonly AIDATA_UUID="8c898220-2bac-41b5-9987-16a3c90bbe11"
readonly AIDATA_DEVICE="/dev/disk/by-uuid/${AIDATA_UUID}"
readonly AIDATA_MOUNT="/data"
readonly FSTAB_FILE="/etc/fstab"
readonly FSTAB_BACKUP="/etc/fstab.backup-before-aidata-20260809"
readonly FSTAB_ENTRY="UUID=${AIDATA_UUID} /data ext4 defaults,nofail,nodev,nosuid,x-systemd.device-timeout=10s 0 2"

if [[ ${EUID} -ne 0 ]]; then
    echo "This script must run as root." >&2
    exit 1
fi

if [[ ! -b "${AIDATA_DEVICE}" ]]; then
    echo "AIdata device not found: ${AIDATA_DEVICE}" >&2
    exit 1
fi

actual_uuid="$(blkid -s UUID -o value "${AIDATA_DEVICE}")"
if [[ "${actual_uuid}" != "${AIDATA_UUID}" ]]; then
    echo "AIdata UUID mismatch; refusing to continue." >&2
    exit 1
fi

if mountpoint -q "${AIDATA_MOUNT}"; then
    mounted_source="$(findmnt -n -o SOURCE --target "${AIDATA_MOUNT}")"
    if [[ "$(readlink -f "${mounted_source}")" != "$(readlink -f "${AIDATA_DEVICE}")" ]]; then
        echo "${AIDATA_MOUNT} is already used by ${mounted_source}; refusing to continue." >&2
        exit 1
    fi
else
    if [[ -e "${AIDATA_MOUNT}" && ! -d "${AIDATA_MOUNT}" ]]; then
        echo "${AIDATA_MOUNT} exists but is not a directory; refusing to continue." >&2
        exit 1
    fi
    if [[ -d "${AIDATA_MOUNT}" ]] && [[ -n "$(find "${AIDATA_MOUNT}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
        echo "${AIDATA_MOUNT} is not empty; refusing to hide existing files." >&2
        exit 1
    fi
    mkdir -p "${AIDATA_MOUNT}"
fi

if grep -Fq "${AIDATA_UUID}" "${FSTAB_FILE}"; then
    if ! grep -Fxq "${FSTAB_ENTRY}" "${FSTAB_FILE}"; then
        echo "A different fstab entry already references AIdata; refusing to modify it." >&2
        exit 1
    fi
elif grep -Eq '^[^#].*[[:space:]]/data[[:space:]]' "${FSTAB_FILE}"; then
    echo "A different fstab entry already uses /data; refusing to modify it." >&2
    exit 1
else
    if [[ -e "${FSTAB_BACKUP}" ]]; then
        echo "Backup already exists: ${FSTAB_BACKUP}; refusing to overwrite it." >&2
        exit 1
    fi
    cp -a "${FSTAB_FILE}" "${FSTAB_BACKUP}"
    printf '\n# 595 GB AIdata partition (configured 2026-08-09)\n%s\n' "${FSTAB_ENTRY}" >>"${FSTAB_FILE}"
fi

systemctl daemon-reload
if ! mountpoint -q "${AIDATA_MOUNT}"; then
    mount "${AIDATA_MOUNT}"
fi

mounted_source="$(findmnt -n -o SOURCE --target "${AIDATA_MOUNT}")"
if [[ "$(readlink -f "${mounted_source}")" != "$(readlink -f "${AIDATA_DEVICE}")" ]]; then
    echo "Post-mount source verification failed." >&2
    exit 1
fi

echo "AIdata mounted successfully at ${AIDATA_MOUNT}."
