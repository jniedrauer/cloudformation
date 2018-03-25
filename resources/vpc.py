"""Wrappers for rendering VPCs"""

from typing import List
from ipaddress import ip_network

from troposphere import Output, Ref, Tags, Template
from troposphere.ec2 import VPC
from troposphere.ec2 import InternetGateway
from troposphere.ec2 import VPCGatewayAttachment
from troposphere.route53 import HostedZone, HostedZoneVPCs

from .wrapper import Wrapper
from .subnet import SubnetWrapper


def split_list(lst):
    """Split a list in half"""
    half = int(len(lst) / 2)
    return lst[:half], lst[half:]


class VpcWrapper(Wrapper):
    """TODO: Documentation"""

    def __init__(self, name: str, cidr: str, private_subnets: int,
                 public_subnets: int, t: Template, nat_eips: Ref = None,
                 hosted_zones: List[str] = None):

        super().__init__()

        self.azs = self.config.regions[self.config.region].AZs

        self.vpc = t.add_resource(VPC(
            name,
            EnableDnsSupport='true',
            CidrBlock=cidr,
            EnableDnsHostnames='true',
            Tags=Tags(
                Application=Ref('AWS::StackName'),
                Name=name,
            )
        ))

        self.igw = t.add_resource(InternetGateway(
            'InternetGateway',
        ))

        self.igw_attachment = t.add_resource(VPCGatewayAttachment(
            'IgwAttachment',
            VpcId=Ref(self.vpc),
            InternetGatewayId=Ref(self.igw),
        ))

        subnets = ip_network(cidr).subnets(prefixlen_diff=8)
        # Split the possible subnets in half, so we can add private or public
        # subnets later without overlapping
        private, public = split_list(list(subnets))

        self.public_subnets = []
        for idx, subnet in enumerate(public[:public_subnets]):
            self.public_subnets.append(SubnetWrapper(
                cidr=str(subnet),
                idx=idx,
                vpc=Ref(self.vpc),
                az=self.config.region+self.azs[idx % len(self.azs)],
                gateway=Ref(self.igw),
                t=t,
                private=False,
            ))

            if nat_eips and idx < self.config.nat_gws:
                # Create up to MAX_NATGWS NAT gateways in different AZs
                self.public_subnets[idx].add_natgw(idx, nat_eips)

        self.private_subnets = []
        for idx, subnet in enumerate(private[:private_subnets]):
            self.private_subnets.append(SubnetWrapper(
                cidr=str(subnet),
                idx=idx,
                vpc=Ref(self.vpc),
                az=self.config.region+self.azs[idx % len(self.azs)],
                gateway=Ref(self.public_subnets[idx % self.config.nat_gws].natgw),
                t=t,
            ))

        self.output = t.add_output([
            Output(
                'VpcId',
                Description=f'VPCId of {name} VPC',
                Value=Ref(self.vpc),
            ),
        ])

        self.zones = []
        for idx, hosted_zone in enumerate(hosted_zones):
            self.zones.append(t.add_resource(HostedZone(
                f'HostedZone{"Alt" + str(idx) if idx > 0 else ""}',
                Name=hosted_zone,
                VPCs=[
                    HostedZoneVPCs(VPCId=Ref(self.vpc), VPCRegion=self.config.region),
                ],
                HostedZoneTags=Tags(
                    Env=self.config.env,
                ),
            )))

            if idx <= 0:
                self.output = t.add_output([
                    Output(
                        'HostedZone',
                        Description=f'Internal hosted zone',
                        Value=Ref(self.zones[idx]),
                    ),
                ])
