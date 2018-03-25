"""Concourse running in ECS"""


import textwrap
from ipaddress import ip_network

from troposphere import (
    GetAtt,
    Select,
    Ref,
    Parameter,
    Template,
)
from troposphere.ec2 import (
    SecurityGroup,
    SecurityGroupRule,
    SecurityGroupIngress,
)
from troposphere.ecr import (
    Repository,
    LifecyclePolicy,
)
from troposphere.route53 import (
    RecordSetType,
    AliasTarget,
)
from troposphere.iam import (
    Role,
    Policy as TropospherePolicy,
)
from awacs.aws import (
    Allow,
    Action,
    Statement,
    Principal,
    Policy,
)
from awacs.sts import AssumeRole


from meta.config import Config
from resources.ecs import EcsWrapper
from resources.vpc import split_list
from resources.subnet import SubnetWrapper
from resources.alb import AlbWrapper


def render() -> str:
    """Default entrypoint"""
    config = Config()

    t = Template()

    t.add_version('2010-09-09')

    t.add_description('Concourse running in ECS.')

    t.add_parameter(Parameter(
        'StackName',
        Description='Cloudformation stack name',
        Type='String',
    ))

    vpc_id = t.add_parameter(Parameter(
        'VpcId',
        Description='Build VPC',
        Type='AWS::SSM::Parameter::Value<String>',
        Default=f'/{config.env.title()}/VpcId',
    ))

    igw = t.add_parameter(Parameter(
        'Igw',
        Description='Internet gateway',
        Type='AWS::SSM::Parameter::Value<String>',
        Default=f'/{config.env.title()}/InternetGateway',
    ))

    common_sg = t.add_parameter(Parameter(
        'CommonSg',
        Description='Common security group',
        Type='AWS::SSM::Parameter::Value<String>',
        Default=f'/{config.env.title()}/CommonAccessSg',
    ))

    azs = config.regions[config.region].AZs
    public_subnets = []
    subnet_cidrs = ip_network(config.cidr).subnets(prefixlen_diff=8)
    _, public_cidrs = split_list(list(subnet_cidrs))

    public_offset = 2
    for idx, subnet in enumerate(public_cidrs[public_offset:public_offset+2]):
        public_subnets.append(SubnetWrapper(
            cidr=str(subnet),
            idx=idx + public_offset,
            vpc=Ref(vpc_id),
            az=config.region+azs[idx % len(azs)],
            gateway=Ref(igw),
            t=t,
            private=False,
        ))

    alb_sg = t.add_resource(SecurityGroup(
        'AlbSecurityGroup',
        GroupDescription=f'Concourse ALB',
        VpcId=Ref(vpc_id),
        SecurityGroupEgress=[
            SecurityGroupRule(
                CidrIp='0.0.0.0/0',
                FromPort='-1',
                IpProtocol='-1',
                ToPort='-1',
            )
        ],
        SecurityGroupIngress=[
            SecurityGroupRule(
                CidrIp='0.0.0.0/0',
                FromPort='80',
                IpProtocol='tcp',
                ToPort='80',
            ),
            SecurityGroupRule(
                CidrIp='0.0.0.0/0',
                FromPort='443',
                IpProtocol='tcp',
                ToPort='443',
            ),
        ],
    ))

    asg_sg = t.add_resource(SecurityGroup(
        'AsgSg',
        GroupName='ConcourseEcsServers',
        GroupDescription=f'Concourse ECS server autoscaling group',
        VpcId=Ref(vpc_id),
    ))

    t.add_resource(SecurityGroupIngress(
        'FromAlbSg',
        GroupId=Ref(asg_sg),
        SourceSecurityGroupId=Ref(alb_sg),
        FromPort='-1',
        IpProtocol='-1',
        ToPort='-1',
    ))

    alb = AlbWrapper(
        name='ConcourseAlb',
        subnets=[Ref(i.subnet) for i in public_subnets],
        backend_port=8000,
        security_group=Ref(alb_sg),
        healthcheck={'port': 8000, 'path': '/'},
        targets=[],
        SANs=[
            'concourse.jniedrauer.com',
        ],
        vpc=Ref(vpc_id),
        t=t,
    )

    t.add_resource(RecordSetType(
        'AlbPublicDns',
        HostedZoneId=config.public_hosted_zone_id,
        Name=f'concourse.{config.public_hosted_zone}',
        Type='A',
        AliasTarget=AliasTarget(
            HostedZoneId=config.regions[config.region].ELB_zone,
            DNSName=GetAtt(alb.alb, 'DNSName'),
        ),
    ))

    ecs_role = t.add_resource(Role(
        'EcsRole',
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal('Service', ['ec2.amazonaws.com'])
                )
            ]
        ),
        Policies=[
            TropospherePolicy(
                PolicyName='EcrRead',
                PolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action('ecr', 'GetDownloadUrlForLayer'),
                                Action('ecr', 'BatchGetImage'),
                                Action('ecr', 'BatchCheckLayerAvailability'),
                                Action('ecr', 'GetAuthorizationToken'),
                            ],
                            Resource=['*'],
                        ),
                    ],
                ),
            ),
            TropospherePolicy(
                PolicyName='EcsAgent',
                PolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action('ecs', 'CreateCluster'),
                                Action('ecs', 'RegisterContainerInstance'),
                                Action('ecs', 'DeregisterContainerInstance'),
                                Action('ecs', 'DiscoverPollEndpoint'),
                                Action('ecs', 'Submit*'),
                                Action('ecs', 'Poll'),
                                Action('ecs', 'StartTelemetrySession'),
                            ],
                            Resource=['*'],
                        ),
                    ],
                ),
            ),
        ],
    ))

    t.add_resource(Role(
        'EcsServiceRole',
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal('Service', ['ecs.amazonaws.com'])
                )
            ]
        ),
        Policies=[
            TropospherePolicy(
                PolicyName='LoadBalancing',
                PolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action('elasticloadbalancing',
                                       'DeregisterInstancesFromLoadBalancer'),
                                Action('elasticloadbalancing', 'DeregisterTargets'),
                                Action('elasticloadbalancing', 'Describe*'),
                                Action('elasticloadbalancing', 'RegisterInstancesWithLoadBalancer'),
                                Action('elasticloadbalancing', 'RegisterTargets'),
                                Action('ec2', 'Describe*'),
                                Action('ec2', 'AuthorizeSecurityGroupIngress'),
                            ],
                            Resource=['*'],
                        ),
                    ],
                ),
            ),
        ],
    ))

    EcsWrapper(
        subnets=[Ref(i.subnet) for i in public_subnets],
        security_groups=[
            Ref(common_sg),
            Ref(asg_sg),
        ],
        size='t2.micro',
        cluster_name='Concourse',
        min_size=1,
        max_size=2,
        role=Ref(ecs_role),
        t=t,
    )

    return t.to_yaml(long_form=True)
