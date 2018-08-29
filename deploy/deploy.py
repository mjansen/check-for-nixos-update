# Deploy a Lambda Function Project

import botocore
import boto3

import yaml

topDir = '..'

def cloudformationTemplateCheck0(t):
    """Check that the template is a dict.

    YAML could also produce and array or a scalar value, and that
    would not make a good cloudformation template.  This check then
    allows further checks to assume that they are working on a dict
    structure.

    """
    return type(t) is dict

def cloudformationTemplateCheck1(t):
    """Check that only the allowed top level keys appear in the template.

    And also make sure that each key appears at most once.  The YAML
    parser may well make sure of that already, but if it does not, the
    test is simply the second test below.

    """
    topLevelKeys = set([ 'AWSTemplateFormatVersion',
                         'Description',
                         'Metadata',
                         'Parameters',
                         'Mappings',
                         'Conditions',
                         'Transform',
                         'Resources',
                         'Outputs' ])
    ks   = t.keys()
    kset = set(ks)
    return kset.issubset(topLevelKeys) and len(kset) == len(ks)

def check_syntax_for_cloudformation_yaml():
    """Check some aspects of the syntax of the cloudformation template.

    We apply some tests as follows:
    1) does the YAML parse succeed?
    2) do we obtain a dict structure from the parse?
    3) are the keys in the dict suitable for a cloudformation template?
    """
    fileName = topDir + '/' + 'resources.yaml'
    try:
        with open(fileName, 'rb') as stream:

            def default_ctor(loader, tag_suffix, node):
                # print('b===============')
                # print(loader)
                # print(tag_suffix)
                print(node)
                # print('e===============')
                return tag_suffix + ' ' + str(node.value)

            yaml.add_multi_constructor('', default_ctor)
            result = yaml.load(stream.read())
        print(result.keys())
        return ( cloudformationTemplateCheck0(result) and
                 cloudformationTemplateCheck1(result) )
    except Exception as e:
        print('the resources file does not seem to be valid yaml')
        print(e)
        return False
