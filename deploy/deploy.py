import sys
import os
import hashlib
import cloudformation_template_check
import botocore
import boto3
import time

stackName      = 'check-for-nixos-update'

def compute_version():
    """Compute the sha1 hash of the sources as the current version."""
    m = hashlib.sha1()
    with open(cfTemplateFile, 'rb') as stream:
        m.update(stream.read())
    with open(pySourceFile, 'rb') as stream:
        m.update(stream.read())
    return m.hexdigest()

def findOutput(tag, outputs):
    """Find and output variable for the stack"""
    for o in outputs:
        if o['OutputKey'] == tag:
            return o['OutputValue']
    raise ValueError

if __name__ == '__main__':

    # initially fetch the stack state:

    cf = boto3.client('cloudformation')

    before = cf.describe_stacks(StackName = stackName)
    print(before)
    if 'Stacks' not in before.keys() or len(before['Stacks']) != 1:
        print('we are not getting a good result describing the stack')
        sys.exit(1)
    stateBefore = before['Stacks'][0]

    sourceName     = findOutput('StackLambdaCode', stateBefore['Outputs'])
    templName      = 'resources.yaml'

    topDir = '..'

    cfTemplateFile = topDir + '/' + templName
    pySourceFile   = topDir + '/' + sourceName + '.py'

    # have the source files changed?

    lastVersion = findOutput('StackVersion', stateBefore['Outputs'])
    currVersion = compute_version()

    if lastVersion == currVersion:
        print('no change')
        sys.exit(1)

    # the source files have changed.  run a check on the cloudformation template first.

    if not cloudformation_template_check.check_syntax_for_cloudformation_yaml(cfTemplateFile):
        print('bad cloudformation template')
        sys.exit(1)

    # the template is ok.  Now check the python code:

    # the python code is also ok, so let us invoke cloudformation:

    # how is tmp built?
    os.system('cp ' + pySourceFile + ' tmp/')
    print('zipping lambda deployment')
    os.system('cd tmp && zip -qr ../{}.zip *'.format(currVersion))
    print('uploading to s3')

    zipFile   = '{}.zip'.format(currVersion)

    # the bucket does not exist until we have created the stack, or at
    # least a part of it that creates the bucket.  Perhaps all stacks
    # should have a stack-bucket they can refer to.

    bucket = findOutput('StackBucket', stateBefore['Outputs'])

    s3 = boto3.resource('s3')

    s3.Object(bucket, zipFile).upload_file(zipFile)
    print('done uploading')

    with open(cfTemplateFile, 'rb') as stream:
        t = stream.read().decode('utf-8').replace('__VERSION__', currVersion)

    try:
        result = cf.update_stack(StackName = stackName, TemplateBody = t, Capabilities = [ 'CAPABILITY_IAM' ])
    except botocore.exceptions.ClientError as e:
        print('===========')
        print(e)
        print('===========')
        if str(e) == 'An error occurred (ValidationError) when calling the UpdateStack operation: No updates are to be performed.':
            saveVersion(currVersion)
            sys.exit(1)
        raise

    print(result)

    while True:
        after = cf.describe_stacks(StackName = stackName)
        print(after)
        status = after['Stacks'][0]['StackStatus']
        print('status =', status)
        if after['Stacks'][0]['LastUpdatedTime'] != before['Stacks'][0]['LastUpdatedTime']:
            if status.find('COMPLETE') >= 0:
                break
        time.sleep(15)

    sys.exit(0)
