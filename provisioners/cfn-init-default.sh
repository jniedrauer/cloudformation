#!/usr/bin/env bash

set -eux

main() {
    yum -y update

    printf '\n%%wheel ALL=(ALL) NOPASSWD: ALL\n' >>/etc/sudoers

    add_user \
        jniedrauer \
        'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDZxuzrQfHmOhXXadbDXzcSrNe0pCKx7/DLCYOk2cWgr jniedrauer@homeserver'
}

add_user() {
    user="$1"
    pubkey="$2"
    getent passwd "$user" >/dev/null 2>&1 \
        || useradd -G wheel "$user"
    su "$user" -c 'mkdir -p ~/.ssh -m 0700'
    su "$user" -c 'umask 077; touch ~/.ssh/authorized_keys'
    echo "$pubkey" >"/home/$user/.ssh/authorized_keys"
}

main
