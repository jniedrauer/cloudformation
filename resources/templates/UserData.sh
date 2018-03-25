#!/bin/bash -x

/usr/bin/easy_install \
    --script-dir /opt/aws/bin \
    https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
cp -v \
    /usr/lib/python2*/site-packages/aws_cfn_bootstrap*/init/redhat/cfn-hup \
    /etc/init.d

chmod 0755 /etc/init.d/cfn-hup

export PATH=$PATH:/opt/aws/bin

cfn-init -v \
    --stack ${AWS::StackName} \
    --resource {{ resource }} \
    --region ${AWS::Region}

cfn-signal -e $? \
    --stack ${AWS::StackName} \
    --resource {{ resource }} \
    --region ${AWS::Region}
