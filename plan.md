As this check is to run just once a day, it seems like overkill to run
it on an instance, even if that instance is already up for a different
purpose.  So we can look at a simple serverless implementation.  The
migration is from an implementation that uses local machine resources
(here we use just disk via EBS) to one that uses a cloud resources,
the correct choice here being S3.

step 1: store the configuration and state files in S3

step 2: set up a lambda triggered by a cloudwatch (cron) event

step 3: add logging to cloudwatch logs

To do this we simply extend the cloudformation script to provision
these resources.