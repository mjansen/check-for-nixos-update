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
    if type(t) is dict:
        return True
    else:
        print('error: the result of the YAML parse is not a dictionary')
        return False

def cloudformationTemplateCheck1(t):
    """Check that the correct top level keys appear in the template.

    And also make sure that each key appears at most once.  The YAML
    parser may well make sure of that already, but if it does not, the
    test is simply the second test below.

    Also make sure that there is a Resources section, as this is the
    (only) required section.

    """
    requiredKeys = set([ 'Resources' ])
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

    ok = True

    if not (kset.issubset(topLevelKeys) and len(kset) == len(ks)):
        print('error: unexpected top level sections in template:', kset.difference(topLevelKeys))
        print('info: the allowed sections are', topLevelKeys)
        ok = False

    if not kset.issuperset(requiredKeys):
        print('error: the Resources section is required')
        ok = False

    return ok

def check_syntax_for_cloudformation_yaml(fileName):
    """Check some aspects of the syntax of the cloudformation template.

    We apply some tests as follows:

    1) does the YAML parse succeed?
    2) do we obtain a dict structure from the parse?
    3) are the keys in the dict suitable for a cloudformation template?

    Possible extension checks:

    4) are the ! constructors Ref GetAtt Join etc?

    5) does a !Ref refer to a resource or parameter or condition etc
       (second level key) name, or is it a more complex structure such as
       a Fn::Join, in which case we should at least give a warning.

    6) does !GetAtt get 2 arguments (the first one should likely be a string, the second one also)

    7) does !Join get an array of type [ str [ str ]]?

    8) do resources have the correct structure

    9) do resource properties have the right keys?

    """
    try:
        with open(fileName, 'rb') as stream:

            def default_ctor(loader, tag_suffix, node):
                # print('b===============')
                # print(loader)
                # print(tag_suffix)
                print('notice:', node)
                # print('e===============')
                return tag_suffix + ' ' + str(node.value)

            yaml.add_multi_constructor('', default_ctor)
            parseResult = yaml.load(stream.read())
    except Exception as e:
        print('the resources file does not seem to be valid yaml')
        print(e)
        return False

    tests = [ cloudformationTemplateCheck0,
              cloudformationTemplateCheck1 ]
    return all(map(lambda c: c(parseResult), tests))

if __name__ == '__main__':
    templateFile = topDir + '/' + 'resources.yaml'
    templateFile = 'resources.yaml'
    check_syntax_for_cloudformation_yaml(templateFile)
