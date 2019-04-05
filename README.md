![amira](https://raw.githubusercontent.com/Yelp/amira/master/amira_github_banner.png)

[![PyPI](https://img.shields.io/pypi/v/amira.svg)](https://pypi.python.org/pypi/amira)
[![Build Status](https://travis-ci.org/Yelp/amira.svg?branch=master)](https://travis-ci.org/Yelp/amira)

# AMIRA: Automated Malware Incident Response & Analysis

AMIRA is a service for automatically running the analysis on the
[OSXCollector](https://github.com/Yelp/osxcollector) output files.
The automated analysis is performed via
[OSXCollector Output Filters](https://github.com/Yelp/osxcollector_output_filters),
in particular *The One Filter to Rule Them All*: the
[Analyze Filter](https://github.com/Yelp/osxcollector_output_filters#analyzefilter---the-one-filter-to-rule-them-all).
AMIRA takes care of retrieving the output files from an S3 bucket,
running the Analyze Filter and then uploading the results
of the analysis back to S3 (although one could envision as well
attaching them to the related JIRA ticket).

## Prerequisites

### tox

The following steps assume you have [tox](http://tox.readthedocs.org/)
installed on your machine.

If this is not the case, please run:
```bash
$ sudo pip install tox
```

### OSXCollector Output Filters configuration file

AMIRA uses OSXCollector Output Filters to do the actual analysis,
so you will need to have a valid `osxcollector.yaml`
configuration file in the working directory.
The example configuration file can be found in the
[OSXCollector Output Filters](https://github.com/Yelp/osxcollector_output_filters/blob/master/osxcollector.yaml.example).

The configuration file mentions the location of the file hash and the domain
blacklists.
Make sure that the blacklist locations mentioned in the configuration file are
also available when running AMIRA.

### AWS credentials

AMIRA uses boto to interface with AWS.
You can supply the credentials using either of the possible
[boto config files](http://boto.cloudhackers.com/en/latest/boto_config_tut.html#details).

The credentials should allow reading and deleting SQS messages
from the SQS queue specified in the AMIRA config as well as
the read access to the objects in the S3 bucket where the OSXCollector
output files are stored.
To be able to upload the analysis results back to the S3 bucket
specified in the AMIRA configuration file, the credentials should
also allow write access to this bucket.

## AMIRA Architecture

The service uses the
[S3 bucket event notifications](http://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html)
to trigger the analysis.
You will need to configure an S3 bucket for the OSXCollector output files,
so that when a file is added there the notification will be sent to an SQS queue
(`AmiraS3EventNotifications` in the picture below).
AMIRA periodically checks the queue for any new messages
and upon receiving one it will fetch the OSXCollector output file from the S3
bucket.
It will then run the Analyze Filter on the retrieved file.

The Analyze Filter runs all the filters contained in the OSXCollector Output
Filters package sequentially. Some of them communicate with the external
resources, like domain and hashes blacklists (or whitelists) and threat intel
APIs, e.g. [VirusTotal](https://github.com/Yelp/threat_intel#virustotal-api),
[OpenDNS Investigate](https://github.com/Yelp/threat_intel#opendns-investigate-api)
or [ShadowServer](https://github.com/Yelp/threat_intel#shadowserver-api).
The original OSXCollector output is extended with all of this information and
the very last filter run by the Analyze Filter summarizes all of the findings
into a human-readable form. After the filter finishes running, the results of
the analysis will be uploaded to the Analysis Results S3 bucket.

The overview of the whole process and the system components involved in it are
depicted below:

![component diagram](https://github.com/Yelp/amira/raw/master/doc/component_diagram.png "Component Diagram")

## Using AMIRA

The main entry point to AMIRA is in the `amira/amira.py` module.
You will first need to create an instance of AMIRA class by providing the AWS
region name, where the SQS queue with the event notifications for the
OSXCollector output bucket is, and the SQS queue name:

```python
from amira.amira import AMIRA

amira = AMIRA('us-west-1', 'AmiraS3EventNotifications')
```

Then you can register the analysis results uploader, e.g. the S3 results
uploader:

```python
from amira.s3 import S3ResultsUploader

s3_results_uploader = S3ResultsUploader('amira-results-bucket')
amira.register_results_uploader(s3_results_uploader)
```

Finally, run AMIRA:
```python
amira.run()
```

Go get some coffee, sit back, relax and wait till the analysis results pop up
in the S3 bucket!
