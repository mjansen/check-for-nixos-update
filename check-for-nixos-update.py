#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python36.withPackages(ps: [ ps.pyyaml ps.certifi ps.urllib3 ps.botocore ps.boto3 ])"

import yaml
import os
import urllib3
import json
import certifi
import boto3
import botocore

def nixosChannelURL(nixosVersion):
    return ('https://nixos.org/channels/nixos-' + nixosVersion + '/')

def loadConfig(str):
    try:
        return (yaml.load(str))
    except yaml.YAMLError as exc:
        print(exc)
        raise(exc)

def sendSlackMessage(connPool, slackURL, msg):
    data = { 'text': msg }
    encoded_data = json.dumps(data).encode('utf-8')
    result = connPool.request('POST', slackURL,
                     body=encoded_data,
                     headers={'Content-Type': 'application/json'})
    if result.status == 200 and result.data == 'ok':
        print('cannot send to slack: status = {}, data = {}'.format(result.status, result.data))

BUCKET_NAME = os.environ['BUCKET_NAME']

def my_handler(event, context):
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

if __name__ == '__main__':
  result = my_handler(None, None)
  print(result)
