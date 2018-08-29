import sys
import os
import hashlib
import cloudformation_template_check
import botocore
import boto3
import time

topDir = '..'

cfTemplateFile = topDir + '/' + 'resources.yaml'
pySourceFile   = topDir + '/' + 'check_for_nixos_update.py'

lastDeployedVersionFile = 'lastDeployedVersion'

def compute_version():
    """Compute the sha1 hash of the sources as the current version."""
    m = hashlib.sha1()
    with open(cfTemplateFile, 'rb') as stream:
        m.update(stream.read())
    with open(pySourceFile, 'rb') as stream:
        m.update(stream.read())
    return m.hexdigest()

def readLastVersion():
    """Read the last published version from disk, returned as a string.."""
    # we should read from S3 or cloudformation
    try:
        with open(lastDeployedVersionFile, 'rb') as stream:
            lastVersion = stream.read().decode('utf-8')
    except:
        lastVersion = ''

    return lastVersion

def saveVersion(version):
    """Save the currently deployed version to the file system."""
    # we should write to S3 or cloudformation
    with open(lastDeployedVersionFile, 'wb') as stream:
        stream.write(version.encode('utf-8'))

if __name__ == '__main__':

    # have the source files changed?

    lastVersion = readLastVersion()
    currVersion = compute_version()

    print(lastVersion)
    print(currVersion)

    if lastVersion == currVersion:
        print('no change')
        sys.exit(1)

    # the source files have changed.  run a check on the cloudformation template first.

    if not cloudformation_template_check.check_syntax_for_cloudformation_yaml(cfTemplateFile):
        print('bad cloudformation template')
        sys.exit(1)

    # the template is ok.  Now check the python code:

    # the python code is also ok, so let us invoke cloudformation:

    os.system('cat ../resources.yaml | sed -e "s/VERSION/{}/" > resources.yaml'.format(currVersion))
    # how is tmp built?
    os.system('cp ' + pySourceFile + ' tmp/check_for_nixos_update.py')
    print('zipping lambda deployment')
    os.system('cd tmp && zip -qr ../{}.zip *'.format(currVersion))
    print('uploading to s3')

    s3 = boto3.resource('s3')
    bucket = 'check-for-nixos-update-mybucket-1odydo854iyre'
    zipFile = '{}.zip'.format(currVersion)
    s3.Object(bucket, zipFile).upload_file(zipFile)
    print('done uploading')

    cf = boto3.client('cloudformation')

    before = cf.describe_stacks(StackName = 'check-for-nixos-update')
    print(before)

    with open('resources.yaml', 'rb') as stream:
        t = stream.read().decode('utf-8')

    try:
        result = cf.update_stack(StackName = 'check-for-nixos-update', TemplateBody = t, Capabilities = [ 'CAPABILITY_IAM' ])
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
        after = cf.describe_stacks(StackName = 'check-for-nixos-update')
        print(after)
        status = after['Stacks'][0]['StackStatus']
        print('status =', status)
        if after['Stacks'][0]['LastUpdatedTime'] != before['Stacks'][0]['LastUpdatedTime']:
            if status.find('COMPLETE') >= 0:
                break
        time.sleep(10)

    saveVersion(currVersion)
    sys.exit(0)
