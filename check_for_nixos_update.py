#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python36.withPackages(ps: [ ps.pyyaml ps.certifi ps.urllib3 ps.botocore ps.boto3 ])"

import boto3
import botocore
import certifi
import json
import os
import urllib3
import yaml

def nixosChannelURL(nixosVersion):
    """returns the URL associated with the channel for a specific version of NIXOS.

    This URL will redirect to a specific NIXOS release URL, and we
    will use the redirect location later to determine the current
    release for that version.

    """
    return ('https://nixos.org/channels/nixos-{}/'.format(nixosVersion))

def loadConfig(str):
    """parse the YAML format configuration string and return the configuration dict"""
    try:
        return (yaml.load(str))
    except Exception as e:
        print(e)
        print(str)
        raise(e)

def sendSlackMessage(connPool, slackURL, msg):
    """Send a simple message to a slack channel.

    The channel to send to is implicit in the URL used to submit the
    request to slack.com.

    """
    data = { 'text': msg }
    encoded_data = json.dumps(data).encode('utf-8')
    result = connPool.request('POST', slackURL,
                     body=encoded_data,
                     headers={'Content-Type': 'application/json'})
    if result.status == 200 and result.data == 'ok':
        print('cannot send to slack: status = {}, data = {}'.format(result.status, result.data))

BUCKET_NAME = os.environ['BUCKET_NAME']

def my_handler(event, context):

    """handle an AWS Lambda function invokatio to check the current release of the configured NIXOS version

    Send a message is sent to slack.  We add more text if it looks as
    though there has been a new NIXOS release since the last time we
    checked.

    """
    print(event)
    # print(context)
    s3 = boto3.resource('s3')

    try:
        cfgStr = s3.Object(BUCKET_NAME, 'config.yaml').get()['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("cannot find the configuration file 'config.yaml'.")
        else:
            raise

    try:
        oldLocation = s3.Object(BUCKET_NAME, 'lastRelease').get()['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("cannot find the object 'lastRelease'.  This will be created.")
            oldLocation = ''

    # fetch our parameters from the configuration file:

    cfg = loadConfig(cfgStr)
    nixosVersion = cfg['nixosVersion']
    slackURL     = cfg['slackURL']

    # query nixos.org to examine what the latest release of this nixos version is:

    connPool    = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    result      = connPool.request('HEAD', nixosChannelURL(nixosVersion), redirect=False)
    newLocation = result.headers['Location']

    if newLocation != oldLocation:
        try:
            s3.Object(BUCKET_NAME, 'lastRelease').put(Body = newLocation.encode('utf-8'))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("cannot upload the object 'lastRelease'.")
                raise

    # now inform the slack channel of the current release of that nixos version:

    msg = ''.join(['nixos ', nixosVersion, ' is now at ', newLocation])
    if oldLocation != newLocation:
        msg = msg + '\n' + 'NOTA BENE that this is a new version!'
    sendSlackMessage(connPool, slackURL, msg)

    return { "message" : "all done" }

# testing from the command line:

if __name__ == '__main__':
  result = my_handler(None, None)
  print(result)
