# check-for-nixos-update
A simple python script to check for the current release of a specified nixos version, and notify a slack channel.

This can be run from cron as with the following configuration:

```
5 7 * * * /home/mjansen/source/check-for-nixos-update/cron_command.py
```
