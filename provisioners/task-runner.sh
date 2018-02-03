#!/usr/bin/env bash

set -eux

SERVICES=(
    task-runner
)

PACKAGES=(
    java-1.8.0-openjdk
)

main() {
    install_packages
    enable_services
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

main "$@"
