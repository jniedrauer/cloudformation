#!/usr/bin/env python3
"""Generate parameters file using SSM and write to a temp file"""


import argparse
import json
import tempfile

import boto3


SECRET_IDENTIFIER = 'CfnSecret'


def main():
    """Commandline entrypoint"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--env', required=True, help='target environment')
    parser.add_argument('-n', '--name', required=True, help='stack name')
    args = parser.parse_args()

    ssm = boto3.client('ssm')
    response = ssm.get_parameters_by_path(
        Path='/'.join([
            '/' + args.env.title(),
            SECRET_IDENTIFIER,
            args.name,
        ]),
        Recursive=False,
        WithDecryption=True,
    )

    params = [
        {
            'ParameterKey': i['Name'].split('/')[-1],
            'ParameterValue': i['Value']
        }
        for i in response['Parameters']
    ]

    params.append({
        'ParameterKey': 'StackName',
        'ParameterValue': args.name
    })

    with tempfile.NamedTemporaryFile(delete=False) as tmpf:
        tmpf.write(
            json.dumps(params).encode(),
        )
        print(tmpf.name)


if __name__ == '__main__':
    main()
