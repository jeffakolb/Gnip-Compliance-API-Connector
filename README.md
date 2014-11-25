# Introduction

To ensure that the Twitter user's voice is continually respected, 
Gnip's customers are obligated to maintain compliant data stores...
meaning that requests to delete or otherwise alter data
are acted on and propagated through the customer's data 
analysis framework. To enable customers to comply, Gnip provides
a API endpoint from which all compliance data related to a customer's
account can be regularly requested. A full description of the API
can be found at the [Gnip support site](http://support.gnip.com/apis/compliance_api/).
While the linked documentation provides a complete description of a single query,
this package:
* automates the query generation
* automates the periodic submission of queries
* manages common connection errors
* standardizes the data output

The recommended practice is to query the API for 10-minute time intervalss, 
with a delay of at least 5 minutes between the end of the time interval 
and the current time. Missed data can be obtained with a
series of custom queries of no more than 10 minutes in length. 

To accomodate these modes of operation, 
this package provides two modes of connecting to the API: "real\_time" and "one\_time".
In the "one\_time" mode, the user directly specifies a time window of up to 10 minutes 
in duration. In the "real\_time" mode, the API is periodically polled for the
latest data. Queries in this mode are automatically made when the stop time
if the upcoming query is 5 minutes behind the current time. 

It should be emphasized that, by querying once all time intervals from the time at which
the customer activated their compliance API account to five minutes from the current time,
the customer is guaranteed to recieve all compliance messages relevant to their account.

# Configuration

This software package uses the standard Python configuration file format,
which is parsed by the [ConfigParser](https://docs.python.org/2/library/configparser.html) module. 
The location and name of the config file can be specified with the
`GNIP_CONFIG_FILE` environment variable. Otherwise,
the config file is expected to be named `gnip.cfg`,
and to live in the directory from which the executable script (`src/GnipComplianceApiConnector.py`) is run.
A template config file can be found at `gnip_template.cfg`.


## General configuration options

Python config files contain hierarchical "blocks", each of which contain individual parameter names and values.

The `auth` block specifies the user's Gnip username and password 
with the following parameters: `username` and `password`.
Setting these parameters is required.

The `sys` block contains one, required parameter: `log_file_path`.

The `endpoint` block contains two, required parameters: `endpoint_url` and `endpoint_name`, 
which specifies the API endpoint URL and a user-chosen name for it.
This name will be used in the output file names.

The `proc` block has one, required parameter: `file_path`, 
which specifies the location of the output files.

## Run options

The `run` block specifies the mode of running and associated parameters.
The one required parameter is `run_mode`, and it must have the value
"one\_time" or "real\_time". 

For "one\_time" running, `start_time` and `stop_time` must both be specified,
with the YYYYMMDDhhmm format. 

For "real\_time" running, the only required
parameter is `run_mode`. The user can optionally set:

* `sleep_time_in_seconds` - wait period between checks for a new query; default is 10
* `query_length_in_second` - length between start and stop time; default is 600
* `start_time` - time at which to begin a continuous set of queries
* `time_offset_in_seconds` - defines the start time for the initial query as an offset from the current time

`start_time` and `time_offset_in_seconds` must not both be set. If neither are set,
the start time of the initial query will be 15 minutes behind the current time.

Whether the stop time is set explicity in the config, 
or automatically inside the program,
the API returns data up to but excluding the minute
in the stop time. 

# Running the application

To run the application, simply do: `> python src/GnipComplianceApiConnector.py`
from the repo after having created an appropriate version of `gnip.cfg`. 
