#!/usr/bin/env bash

set -eux

ADMIN_GROUPS=(
    wheel
)

SERVICES=(
)

PACKAGES=(
)

main() {
    hostname="$1"
    IFS=',' read -r -a users <<< "$2"
    for user in "${users[@]}"; do
        add_user "$user"
    done

    set_hostname
    install_packages
    enable_services
    set_sudoers
}

set_hostname() {
    sed -i'' "s/^HOSTNAME=.*/HOSTNAME=$hostname/" /etc/sysconfig/network
    echo "$hostname" >/etc/hostname
    if test -f /etc/cloud/cloud.cfg; then
        sed -i'' "s/^preserve_hostname:.*/preserve_hostname: true/" \
            /etc/cloud/cloud.cfg
    fi
    hostname "$hostname"
}

install_packages() {
    test -n "${PACKAGES:-}" \
        && yum -y install "${PACKAGES[@]}" \
        || return 0
}

enable_services() {
    for service in "${SERVICES[@]:-}"; do
        systemctl enable "$service"
        systemctl start "$service"
    done
}

set_sudoers() {
    for group in "${ADMIN_GROUPS[@]:-}"; do
        (umask 337; touch "/etc/sudoers.d/$group";)
        printf '%%%s ALL=(ALL) NOPASSWD: ALL\n' "$group" >>"/etc/sudoers.d/$group"
    done
}

add_user() {
    IFS=';' read -r -a userdetails <<< "$1"
    user="${userdetails[0]}"
    pubkeys=("${userdetails[@]:1}")
    getent passwd "$user" >/dev/null 2>&1 \
        || useradd -G wheel "$user"
    su "$user" -c 'mkdir -p ~/.ssh -m 0700'
    su "$user" -c 'umask 077; touch ~/.ssh/authorized_keys'
    for pubkey in "${pubkeys[@]}"; do
        echo "$pubkey" >>"/home/$user/.ssh/authorized_keys"
    done
}

main "$@"
