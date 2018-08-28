#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python36.withPackages(ps: [ ps.pyyaml ps.certifi ps.urllib3 ps.botocore ps.boto3 ])"

import yaml
import os
import urllib3
import json
import certifi
import boto3
import botocore

configFile  = '/tmp/config.yaml'
lastRelease = '/tmp/lastRelease'

def nixosChannelURL(nixosVersion):
    return ('https://nixos.org/channels/nixos-' + nixosVersion + '/')

def loadConfig():
    with open(configFile, 'r') as stream:
        try:
            return (yaml.load(stream))
        except yaml.YAMLError as exc:
            print(exc)
            raise(exc)

def readContent(fileName):
    try:
        with open(fileName, 'r') as stream:
            return stream.read()
    except:
        return ''

def writeContent(fileName, myData):
    with open(fileName, 'w') as stream:
        stream.write(myData)

def sendSlackMessage(connPool, slackURL, msg):
    data = { 'text': msg }
    encoded_data = json.dumps(data).encode('utf-8')
    result = connPool.request('POST', slackURL,
                     body=encoded_data,
                     headers={'Content-Type': 'application/json'})
    if result.status == 200 and result.data == 'ok':
        print('cannot send to slack: status = {}, data = {}'.format(result.status, result.data))

BUCKET_NAME = os.environ['BUCKET_NAME']
KEY = 'config.yaml'

def my_handler(event, context):
    print(event)
    print(context)
    s3 = boto3.resource('s3')

    try:
        s3.Object(BUCKET_NAME, 'config.yaml').download_file('/tmp/config.yaml')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("cannot find the configuration file 'config.yaml'.")
        else:
            raise

    try:
        s3.Object(BUCKET_NAME, 'lastRelease').download_file(lastRelease)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("cannot find the object 'lastRelease'.  This will be created.")

    # fetch our parameters from the configuration file:

    cfg = loadConfig()
    os.remove('/tmp/config.yaml')
    nixosVersion = cfg['nixosVersion']
    slackURL     = cfg['slackURL']

    # we read the last release URL to later compare it with the current one:

    oldLocation = readContent(lastRelease)

    # query nixos.org to examine what the latest release of this nixos version is:

    connPool    = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    result      = connPool.request('HEAD', nixosChannelURL(nixosVersion), redirect=False)
    newLocation = result.headers['Location']
    writeContent(lastRelease, newLocation)

    try:
        s3.Object(BUCKET_NAME, 'lastRelease').upload_file(lastRelease)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("cannot upload the object 'lastRelease'.")
        raise

    os.remove(lastRelease)

    # now inform the slack channel of the current release of that nixos version:

    msg = ''.join(['nixos ', nixosVersion, ' is now at ', newLocation])
    if oldLocation != newLocation:
        msg = msg + '\n' + 'NOTA BENE that this is a new version!'
    sendSlackMessage(connPool, slackURL, msg)

    return { "message" : "all done" }

if __name__ == '__main__':
  result = my_handler(None, None)
  print(result)
