"""Wrappers for creating ALBs"""


from typing import List

from troposphere import Ref, Tags, Template
from troposphere.certificatemanager import Certificate
from troposphere.elasticloadbalancingv2 import LoadBalancer
from troposphere.elasticloadbalancingv2 import Matcher
from troposphere.elasticloadbalancingv2 import Action
from troposphere.elasticloadbalancingv2 import TargetGroup
from troposphere.elasticloadbalancingv2 import Listener
from troposphere.elasticloadbalancingv2 import TargetDescription
from troposphere.elasticloadbalancingv2 import Certificate as AlbCertificate
from troposphere.elasticloadbalancingv2 import TargetGroupAttribute

from .wrapper import Wrapper


class AlbWrapper(Wrapper):
    """TODO: Documentation"""

    def __init__(self, name: str, subnets: List[Ref], backend_port: int,
                 security_group: Ref, targets: List[Ref],
                 healthcheck: dict, SANs: List[str], vpc: Ref, t: Template):

        super().__init__()


        self.alb = t.add_resource(LoadBalancer(
            name,
            Name=name,
            Scheme='internet-facing',
            SecurityGroups=[security_group],
            Subnets=subnets,
            Tags=Tags(
                Env=self.config.env
            ),
        ))

        self.target = t.add_resource(TargetGroup(
            f'{name}Target',
            HealthCheckIntervalSeconds=30,
            HealthCheckPath=healthcheck['path'],
            HealthCheckPort=healthcheck['port'],
            HealthCheckProtocol='HTTP',
            HealthCheckTimeoutSeconds=10,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2,
            Matcher=Matcher(
                HttpCode='200',
            ),
            Port=backend_port,
            Protocol='HTTP',
            Targets=[
                TargetDescription(
                    Id=i,
                )
                for i in targets
            ],
            VpcId=vpc,
            TargetGroupAttributes=[TargetGroupAttribute(
                Key='deregistration_delay.timeout_seconds',
                Value='30',
            )],
        ))

        self.cert = t.add_resource(Certificate(
            f'{name}Certificate',
            DomainName=SANs[0],
            SubjectAlternativeNames=SANs
        ))

        t.add_resource(Listener(
            f'{name}HttpListener',
            Port='80',
            Protocol='HTTP',
            LoadBalancerArn=Ref(self.alb),
            DefaultActions=[
                Action(
                    Type='forward',
                    TargetGroupArn=Ref(self.target)
                )
            ]
        ))

        t.add_resource(Listener(
            f'{name}HttpsListener',
            Port='443',
            Protocol='HTTPS',
            LoadBalancerArn=Ref(self.alb),
            Certificates=[
                AlbCertificate(
                    CertificateArn=Ref(self.cert),
                ),
            ],
            DefaultActions=[
                Action(
                    Type='forward',
                    TargetGroupArn=Ref(self.target),
                ),
            ],
        ))
