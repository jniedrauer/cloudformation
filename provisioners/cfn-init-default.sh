#!/usr/bin/env bash

set -eux

main() {
    yum -y update

    # For debugging only
    add_user \
        jniedrauer \
        'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDZxuzrQfHmOhXXadbDXzcSrNe0pCKx7/DLCYOk2cWgr jniedrauer@homeserver'

    install_packages

    #join_realm
    #enable_services
    set_sudoers

    #reboot
}

install_packages() {
    packages=(
        adcli
        sssd
        realmd
        krb5-workstation
        samba-common-tools
    )
    yum -y install "${packages[@]}"
}

join_realm() {
    realm join --verbose \
        -U Administrator@AD.JNIEDRAUER.LOCAL ad.jniedrauer.local
}

enable_services() {
    services=(
        sssd
    )
    for service in "${services[@]}"; do
        systemctl enable "$service"
        systemctl start "$service"
    done
}

set_sudoers() {
    printf '\n%%wheel ALL=(ALL) NOPASSWD: ALL\n' >>/etc/sudoers
    printf '\n%%Linux\ Admins@ad.jniedrauer.com ALL=(ALL) NOPASSWD: ALL\n' >>/etc/sudoers
}

add_user() {
    # For debugging only
    user="$1"
    pubkey="$2"
    getent passwd "$user" >/dev/null 2>&1 \
        || useradd -G wheel "$user"
    su "$user" -c 'mkdir -p ~/.ssh -m 0700'
    su "$user" -c 'umask 077; touch ~/.ssh/authorized_keys'
    echo "$pubkey" >"/home/$user/.ssh/authorized_keys"
}

main
