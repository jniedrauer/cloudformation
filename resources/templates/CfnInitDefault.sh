#!/usr/bin/env bash
{# Needs `hostname: str` and `volumes: List[dict]` #}
set -eux

hostname={{ hostname }}

sed -i'' "s/^HOSTNAME=.*/HOSTNAME=$hostname/" /etc/sysconfig/network
echo "$hostname" >/etc/hostname
if test -f /etc/cloud/cloud.cfg; then
    sed -i'' "s/^preserve_hostname:.*/preserve_hostname: true/" \
        /etc/cloud/cloud.cfg
fi
hostname "$hostname"

{% for volume in volumes if volume['mountpoint'] != '/' -%}
for prefix in sd xvd; do
    test -b /dev/${prefix}{{ volume['device_id'] }} \
        && device=/dev/${prefix}{{ volume['device_id'] }} \
        && break
done

mkdir -p {{ volume['mountpoint'] }}
mkfs -t ext4 "$device"
echo "$device {{ volume['mountpoint'] }} ext4 defaults,nofail 0 2" >>/etc/fstab
mount -a
{% endfor %}
