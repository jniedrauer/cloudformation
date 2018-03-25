"""Functions for condensing Cloudformation calls"""


import os

from troposphere import Join, Ref


def stack_url(name: str, stack: Ref):
    """Create a substack URL and return it"""
    return Join(
        '/',
        [
            f'https://s3.amazonaws.com/{os.environ["CFN_BUCKET"]}',
            stack,
            name
        ]
    )
