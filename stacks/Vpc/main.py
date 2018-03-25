

from troposphere import Join, Parameter, Ref, Template
from troposphere.ssm import Parameter as SsmParameter
from troposphere.cloudformation import Stack
from troposphere.iam import User
from troposphere.iam import Policy as TropospherePolicy

from awacs.aws import Allow, Action, Statement, Policy

from resources.cfn import stack_url
from resources.vpc import VpcWrapper
from meta.config import Config


def render() -> str:
    """Default entrypoint"""
    config = Config()

    t = Template()

    t.add_version('2010-09-09')

    t.add_description('Base VPC.')

    stack_name = t.add_parameter(Parameter(
        'StackName',
        Description='Cloudformation stack name',
        Type='String',
    ))

    vpc = VpcWrapper(
        name=f'{config.env.title()}Env',
        cidr=config.cidr,
        private_subnets=0,
        public_subnets=2,
        hosted_zones=[
            config.internal_hosted_zone,
        ],
        t=t,
    )

    t.add_resource(SsmParameter(
        'VpcParameter',
        Name=f'/{config.env.title()}/VpcId',
        Type='String',
        Value=Ref(vpc.vpc)
    ))

    t.add_resource(SsmParameter(
        'InternalZoneParameter',
        Name=f'/{config.env.title()}/InternalHostedZone',
        Type='String',
        Value=config.internal_hosted_zone,
    ))

    t.add_resource(SsmParameter(
        'IgwParameter',
        Name=f'/{config.env.title()}/InternetGateway',
        Type='String',
        Value=Ref(vpc.igw)
    ))

    t.add_resource(User(
        f'{config.env.title()}DnsIamUser',
        Path='/automation/',
        Policies=[
            TropospherePolicy(
                PolicyName='Route53AcmeVerify',
                PolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action('route53', 'GetHostedZone'),
                                Action('route53', 'ChangeResourceRecordSets'),
                                Action('route53', 'ListResourceRecordSets'),
                            ],
                            Resource=[
                                f'arn:aws:route53:::hostedzone/{config.public_hosted_zone_id}'],
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action('route53', 'ListHostedZones'),
                                Action('route53', 'ListHostedZonesByName'),
                                Action('route53', 'GetHostedZoneCount'),
                            ],
                            Resource=['*'],
                        ),
                    ],
                )
            ),
        ],
    ))

    return t.to_yaml(long_form=True)
