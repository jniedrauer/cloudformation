#!/bin/bash -x

# TODO: Deprecate this once Amazon Linux 2 LTS ships
yum -y install aws-cfn-bootstrap

export PATH=$PATH:/opt/aws/bin

cfn-init -v \
    --stack ${AWS::StackName} \
    --resource {{ metadata }} \
    --region ${AWS::Region}

cfn-signal -e $? \
    --stack ${AWS::StackName} \
    --resource {{ resource }} \
    --region ${AWS::Region}
