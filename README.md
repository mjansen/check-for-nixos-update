# check-for-nixos-update

The idea is to check the current release of a specified nixos version,
and, if it has changed, notify a slack channel.

The implementation is serverless, i.e. we use a Cloudwatch Scheduled
event to trigger a Lambda to do the check.  The lambda deployment, the
configuration, and the last retrieved state are stored in a bucket.

Deployment is via cloudformation.