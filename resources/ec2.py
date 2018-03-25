"""Wrappers for creating EC2 instances"""

from troposphere import Base64, GetAtt, Sub, Ref, Tags, Template
from troposphere.ec2 import Instance
from troposphere.ec2 import EBSBlockDevice
from troposphere.ec2 import BlockDeviceMapping
from troposphere.policies import CreationPolicy, ResourceSignal
from troposphere.route53 import RecordSetType
from troposphere.cloudformation import (
    Init, InitConfigSets, InitConfig, Metadata
)

from .wrapper import Wrapper


def get_device_mapping(idx):
    """Given an integer, return a unix device"""
    return chr(98+idx) # First device name will be /dev/sdb or /dev/sdc depending on whether or not
                       # the root volume was overriden


class Ec2Wrapper(Wrapper):
    """TODO: Documentation"""

    def __init__(self, subnet: Ref, security_groups: list, size: str, tags: dict, t: Template,
                 profile: Ref = None, volumes: list = None, ami: str = None, managed: bool = True):

        super().__init__()

        self.name = tags['Name']

        tags['Name'] = '.'.join([
            tags['Name'],
            self.config.internal_hosted_zone,
        ])

        self.userdata = self.render_template('UserData.sh',
                                             resource=self.name)
        if not volumes:
            volumes = []
        for idx, volume in enumerate(volumes):
            if volume['mountpoint'] == '/':
                volume['device_id'] = 'a1'
            else:
                volume['device_id'] = get_device_mapping(idx)

            volume['volume'] = EBSBlockDevice(
                f'Volume{idx}',
                VolumeSize=volume['size'],
                VolumeType='gp2',
                DeleteOnTermination=not volume.get('preserve'),
            )

            volume['mapping'] = BlockDeviceMapping(
                DeviceName=f'/dev/sd{volume["device_id"]}',
                Ebs=volume['volume'],
            )

        options = {}
        if profile:
            options.update(dict(
                IamInstanceProfile=profile,
            ))
        if volumes:
            options.update(dict(
                BlockDeviceMappings=[i['mapping'] for i in volumes],
            ))
        if managed:
            options.update(dict(
                UserData=Base64(Sub(self.userdata)),
                Metadata=Metadata(Init(
                    InitConfigSets(
                        default=['default'],
                    ),
                    default=InitConfig(
                        files={
                            '/tmp/CfnInitDefault.sh': {
                                'content': self.render_template(
                                    'CfnInitDefault.sh',
                                    hostname=tags['Name'],
                                    volumes=volumes,
                                ),
                                'mode': '000755',
                                'owner': 'root',
                                'group': 'root',
                            },
                        },
                        commands={
                            '1_default': {
                                'command': '/tmp/CfnInitDefault.sh',
                            },
                        },
                    ),
                )),
                CreationPolicy=CreationPolicy(ResourceSignal=ResourceSignal(
                    Timeout='PT5M',
                    Count=1,
                )),
            ))

        self.instance = t.add_resource(Instance(
            self.name,
            ImageId=ami or self.config.AMIs.centos7['1801_01'][self.config.region],
            InstanceType=size,
            KeyName=self.config.ec2_keypair,
            SecurityGroupIds=security_groups,
            SubnetId=subnet,
            Tags=Tags(**tags, **{'Env': self.config.env}),
            **options,
        ))

        self.dns = t.add_resource(RecordSetType(
            'InstanceDns',
            HostedZoneName=f'{self.config.internal_hosted_zone}.',
            Name=tags['Name'],
            Type='A',
            TTL=600,
            ResourceRecords=[GetAtt(self.instance, 'PrivateIp')],
        ))
