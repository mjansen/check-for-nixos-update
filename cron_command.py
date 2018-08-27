#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python36.withPackages(ps: [ ps.pyyaml ps.certifi ps.urllib3 ])"

import yaml
import os
import urllib3
import json
import certifi

workSpaceDir = '/var/tmp/slack-message-store'
lastRelease  = '/'.join([workSpaceDir, 'last-release'])

def nixosChannelURL(nixosVersion):
    return ('https://nixos.org/channels/nixos-' + nixosVersion + '/')

def loadConfig():
    with open("config.yaml", 'r') as stream:
        try:
            return (yaml.load(stream))
        except yaml.YAMLError as exc:
            print(exc)
            raise(exc)

def createWorkSpace():
    try:
        os.mkdir(workSpaceDir)
    except FileExistsError:
        return

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

if __name__ == '__main__':
    # fetch our parameters from the configuration file:

    cfg = loadConfig()
    nixosVersion = cfg['nixosVersion']
    slackURL     = cfg['slackURL']

    # create the working store, if that does not already exist:

    createWorkSpace()

    # we read the last release URL to later compare it with the current one:

    oldLocation = readContent(lastRelease)

    # query nixos.org to examine what the latest release of this nixos version is:

    connPool    = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    result      = connPool.request('HEAD', nixosChannelURL(nixosVersion), redirect=False)
    newLocation = result.headers['Location']
    writeContent(lastRelease, newLocation)

    # now inform the slack channel of the current release of that nixos version:

    msg = ''.join(['nixos ', nixosVersion, ' is now at ', newLocation])
    if oldLocation != newLocation:
        msg = msg + '\n' + 'NOTA BENE that this is a new version!'
    sendSlackMessage(connPool, slackURL, msg)
