"""
Load secrets from SSM Parameter Store into the environment.

For every environment variable NAME_SSM_PARAMETER that holds the name of an SSM
parameter (normally a SecureString), read that parameter once per cold start and
set NAME to its value, so the rest of the code keeps reading os.environ["NAME"].
A NAME that is already set is left alone. A parameter that cannot be read raises:
the invocation fails visibly instead of running without its credentials.
"""

import os

import boto3

SUFFIX = "_SSM_PARAMETER"


def load_ssm_secrets() -> None:
    wanted = {
        key[: -len(SUFFIX)]: value
        for key, value in os.environ.items()
        if key.endswith(SUFFIX) and value
    }
    pending = {name: param for name, param in wanted.items() if not os.environ.get(name)}
    if not pending:
        return

    ssm = boto3.client("ssm")
    for name, param in pending.items():
        response = ssm.get_parameter(Name=param, WithDecryption=True)
        os.environ[name] = response["Parameter"]["Value"]
