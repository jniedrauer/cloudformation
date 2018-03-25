"""Wrapper class for rendering subnets"""
# pylint: disable=too-few-public-methods,too-many-arguments


from troposphere import Output, Select
from troposphere import GetAtt, Ref, Tags, Template
from troposphere.ec2 import NatGateway
from troposphere.ec2 import EIP
from troposphere.ec2 import Route
from troposphere.ec2 import PortRange
from troposphere.ec2 import NetworkAcl
from troposphere.ec2 import SubnetRouteTableAssociation
from troposphere.ec2 import Subnet
from troposphere.ec2 import RouteTable
from troposphere.ec2 import NetworkAclEntry
from troposphere.ec2 import SubnetNetworkAclAssociation


class SubnetWrapper:
    """Create a subnet, inbound and outbound NACLs, a route table, and a route
    table association."""

    def __init__(self, cidr: str, idx: int, vpc: Ref, az: str,
                 t: Template, gateway: Ref, private=True):
        self.idx = idx
        self.t = t
        self.az = az
        self.natgw = None
        self.nat_eip = None
        vis = 'Private' if private else 'Public'

        self.subnet = t.add_resource(Subnet(
            f'{vis}Subnet{idx}',
            VpcId=vpc,
            CidrBlock=cidr,
            AvailabilityZone=az,
            MapPublicIpOnLaunch=not private,
            Tags=Tags(
                Name=f'{vis}Subnet{idx}',
                Application=Ref('AWS::StackName'),
                Network=vis,
            )
        ))

        self.routetable = t.add_resource(RouteTable(
            f'{vis}RouteTable{idx}',
            VpcId=vpc,
            Tags=Tags(
                Name=f'{vis}RouteTable{idx}',
                Application=Ref('AWS::StackName'),
                Network=vis,
            )
        ))

        self.routetable_assoc = t.add_resource(SubnetRouteTableAssociation(
            f'{vis}RouteTableAssociation{idx}',
            SubnetId=Ref(self.subnet),
            RouteTableId=Ref(self.routetable)
        ))

        self.nacl = t.add_resource(NetworkAcl(
            f'{vis}NetworkAcl{idx}',
            VpcId=vpc,
            Tags=Tags(
                Name=f'{vis}NetworkAcl{idx}',
                Application=Ref('AWS::StackName'),
                Network=vis,
            )
        ))

        self.nacl_rules = {}
        for i in ('in', 'out'):
            self.nacl_rules[i] = t.add_resource(NetworkAclEntry(
                f'{i.title()}Bound{vis}NetworkAclEntry{idx}',
                NetworkAclId=Ref(self.nacl),
                RuleNumber='100',
                Protocol='6',
                PortRange=PortRange(To='65535', From='0'),
                Egress=('true' if i == 'out' else 'false'),
                RuleAction='allow',
                CidrBlock='0.0.0.0/0',
            ))

        self.nacl_assoc = t.add_resource(
            SubnetNetworkAclAssociation(
                f'{vis}SubnetNetworkAclAssociation{idx}',
                SubnetId=Ref(self.subnet),
                NetworkAclId=Ref(self.nacl),
            )
        )

        if private:
            self.default_route = t.add_resource(Route(
                f'NatRoute{idx}',
                RouteTableId=Ref(self.routetable),
                DestinationCidrBlock='0.0.0.0/0',
                NatGatewayId=gateway,
            ))

        else:
            self.default_route = t.add_resource(Route(
                f'{vis}DefaultRoute{idx}',
                RouteTableId=Ref(self.routetable),
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=gateway,
            ))

        t.add_output(Output(
            f'{vis}Subnet{idx}',
            Description=f'SubnetId of {vis}Subnet{idx}',
            Value=Ref(self.subnet),
        ))

    def add_natgw(self, idx: int, nat_eips: Ref = None):
        """Add a NAT gateway to the subnet"""
        if nat_eips:
            eip = Select(idx, nat_eips)
        else:
            self.nat_eip = self.t.add_resource(EIP(
                f'NatEip{self.idx}',
                Domain='vpc',
            ))
            eip = GetAtt(self.nat_eip, 'AllocationId')

        self.natgw = self.t.add_resource(NatGateway(
            f'NatGw{self.idx}',
            AllocationId=eip,
            SubnetId=Ref(self.subnet),
        ))

        self.t.add_output(Output(
            f'NatEip{self.idx}',
            Value=eip,
            Description=f'Nat Gateway Elastic IP for {self.az}',
        ))
