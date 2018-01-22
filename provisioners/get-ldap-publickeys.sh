#!/usr/bin/env bash

set -eu

ldapsearch -LLL \
    '(&(objectClass=User)(name='"$1"'))' \
    'sshPublicKey' \
    | sed -n '/^ /{H;d};/sshPublicKey:/x;$g;s/\n *//g;s/sshPublicKey: //gp'
