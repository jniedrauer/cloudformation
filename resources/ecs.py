"""Wrappers for creating ECS clusters"""


from typing import List

from troposphere import (
    Base64,
    Sub,
    Ref,
    Template,
)
from troposphere.autoscaling import (
    Metadata,
    AutoScalingGroup,
    Tag as AsgTag,
    LaunchConfiguration,
)
from troposphere.ecs import (
    Cluster,
)
from troposphere.iam import InstanceProfile
from troposphere.policies import (
    AutoScalingReplacingUpdate,
    AutoScalingRollingUpdate,
    UpdatePolicy,
)
from troposphere.cloudformation import (
    Init,
    InitConfig,
    InitFiles,
    InitFile,
)

from .wrapper import Wrapper


class EcsWrapper(Wrapper):
    """TODO: Documentation"""

    def __init__(self, subnets: List[Ref], security_groups: list, size: str, role: Ref,
                 cluster_name: str, min_size: int, max_size: int, t: Template):

        super().__init__()

        self.userdata = self.render_template('EcsUserData.sh',
                                             metadata='LaunchConfiguration',
                                             resource='AutoscalingGroup')

        self.cluster = t.add_resource(Cluster(
            'EcsCluster',
            ClusterName=cluster_name,
        ))

        self.instance_profile = t.add_resource(InstanceProfile(
            'EcsInstanceProfile',
            Roles=[role]
        ))

        self.launch_config = t.add_resource(LaunchConfiguration(
            'LaunchConfiguration',
            UserData=Base64(Sub(self.userdata)),
            ImageId=self.config.AMIs.ecs['2017.09'][self.config.region],
            InstanceType=size,
            SecurityGroups=security_groups,
            IamInstanceProfile=Ref(self.instance_profile),
            Metadata=Metadata(
                Init(dict(
                    config=InitConfig(
                        files=InitFiles({
                            '/etc/ecs/ecs.config': InitFile(
                                content=Sub('''\
                                    ECS_CLUSTER=${EcsCluster}
                                '''.strip()),
                                mode="000644",
                                owner="root",
                                group="root",
                            )
                        }),
                    )
                )),
            ),
        ))

        self.asg = t.add_resource(AutoScalingGroup(
            'AutoscalingGroup',
            DesiredCapacity=min_size,
            Tags=[
                AsgTag('Name', cluster_name, True),
                AsgTag('Env', self.config.env, True),
            ],
            LaunchConfigurationName=Ref(self.launch_config),
            MinSize=min_size,
            MaxSize=max_size,
            VPCZoneIdentifier=subnets,
            HealthCheckType='EC2',
            UpdatePolicy=UpdatePolicy(
                AutoScalingReplacingUpdate=AutoScalingReplacingUpdate(
                    WillReplace=True,
                ),
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime='PT5M',
                    MinInstancesInService='1',
                    MaxBatchSize='1',
                    WaitOnResourceSignals=True
                )
            )
        ))
