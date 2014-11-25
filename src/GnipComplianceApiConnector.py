#!/usr/bin/env python
__author__ = "Jeff Kolb"

import ConfigParser
import sys
import time
import os
import copy
import logging
import logging.handlers
import base64
import datetime
import time
import urllib2
import zlib
import gzip

CHUNK_SIZE = 2**17        # decrease for v. low volume streams, > max record size
GNIP_KEEP_ALIVE = 30      # 30 sec gnip timeout

class ComplianceApiClient():
    """
    This class needs to make recurring HTTP requests to the 
    Gnip compliance API, and store the results in an appropriate location.

    The class should also have a one-time request mode 
    in which the start and stop time are specified.
    """
    def __init__(self
        , _endpoint_url
        , _endpoint_name
        , _user_name
        , _password
        , _file_path
        , is_compressed=True
    ):
        logr.info("GnipStreamClient started")
        self.compressed = is_compressed
        logr.info("Stream compressed: %s"%str(self.compressed))
        self.endpoint_name = _endpoint_name
        self.endpoint_url = _endpoint_url
        self.file_path = _file_path 

        self.headers = { "Accept": "*/*",  
            "Content-Type" : "application/json",
            "Connection": "Keep-Alive",
            "Accept-Encoding" : "gzip",
            "Authorization" : "Basic %s"%base64.encodestring(
                "%s:%s"%(_user_name, _password))  }

    def run(self, run_args):
        """
        Set up start and stop time, and make connection.

        "real_time" mode allows for three configurations of the initial query: 
        
        1) Default: the query is made for [15 minutes ago] - [5 mintues ago].

        2) By setting the "time_offset_in_sec" parameter of the "run" block,
        the start time of the first query is given by the current time
        minus the offset.

        3) By setting the "start_time" parameter of the "run" block,
        along with "run_mode"="real_time", the start time of the first query
        can be set manually.
        """
        
        if run_args["run_mode"] == "real_time":

            query_length = int(600)
            if "query_length" in run_args:
                query_length = int(run_args["query_length"])
           
            if "time_offset_in_sec" in run_args:
                time_offset = datetime.timedelta(seconds=int(run_args["time_offset_in_sec"]))
                stop_time = datetime.datetime.utcnow() - time_offset
                start_time = stop_time - datetime.timedelta(0,query_length)
            elif "start_time" in run_args:
                start_time = datetime.datetime.strptime(run_args["start_time"],"%Y%m%d%H%M") 
                stop_time = start_time + datetime.timedelta(0,query_length) 
            else:
                stop_time = datetime.datetime.utcnow() - datetime.timedelta(0,300)
                start_time = stop_time - datetime.timedelta(0,query_length)
            
            while True:
                #logr.info("date/time range is {} to {}".format(str(start_time),str(stop_time)))
                self.make_connection(start_time, stop_time)
                
                # musn't query closer than 5 minutes to present time
                #logr.debug(str(datetime.datetime.utcnow()) + " < " + str(stop_time + datetime.timedelta(0,300)))
                while datetime.datetime.utcnow() < stop_time + datetime.timedelta(0,query_length) + datetime.timedelta(0,300) : 
                    #logr.debug(str(datetime.datetime.utcnow()) + " < " + str(stop_time + datetime.timedelta(0,300)))
                    time.sleep(int(run_args["sleep_time_in_seconds"]))
                
                start_time = copy.deepcopy(stop_time)
                stop_time = start_time + datetime.timedelta(0,query_length)
        
        # if we're running a one-time query
        else:
            start_time = datetime.datetime.strptime(run_args["start_time"],"%Y%m%d%H%M") 
            stop_time = datetime.datetime.strptime(run_args["stop_time"],"%Y%m%d%H%M") 
            self.make_connection(start_time, stop_time)

    def make_connection(self, start_time, stop_time): 
        """
        Make the connection, get and parse response.
        """
        logr.info("Collecting data from {} to {}".format(start_time.strftime("%Y%m%d%H%M"),stop_time.strftime("%Y%m%d%H%M")))
        url = self.endpoint_url + "?fromDate=" + start_time.strftime("%Y%m%d%H%M") + "&toDate=" + stop_time.strftime("%Y%m%d%H%M")
        logr.debug("url: {}".format(url))
        req = urllib2.Request(url, headers=self.headers)
        response = urllib2.urlopen(req, timeout=(1+GNIP_KEEP_ALIVE)) 
        
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)
        self.string_buffer = ""
        while True:
            if self.compressed:
                chunk = decompressor.decompress(response.read(CHUNK_SIZE))
            else:
                chunk = response.read(CHUNK_SIZE)

            if chunk == "":  
                break
            
            self.string_buffer += chunk
        
        # write the data to disk
        file_path = "/".join([
            self.file_path,
            "%d"%start_time.year,
            "%02d"%start_time.month,
            "%02d"%start_time.day,
            "%02d"%start_time.hour 
            ])
        try:
            os.makedirs(file_path) 
        except OSError:
            pass
        
        file_name = self.endpoint_name + "_"
        file_name += "-".join([
                "%d"%start_time.year,
                "%02d"%start_time.month,
                "%02d"%start_time.day])
        file_name += "_%02d%02d"%(start_time.hour, start_time.minute)
        file_name += ".json.gz"

        f = gzip.open(file_path + "/" + file_name,"w") 
        f.write(self.string_buffer)
        f.close()

        self.string_buffer = ""

if __name__ == "__main__":
    if "GNIP_CONFIG_FILE" in os.environ:
        config_file_name = os.environ["GNIP_CONFIG_FILE"]
    else:
        config_file_name = "./gnip.cfg"
        if not os.path.exists(config_file_name):
            print "No configuration file found."
            sys.exit()
    config = ConfigParser.ConfigParser()
    config.read(config_file_name)
    
    # set up connection configuration
    if config.has_section("auth"):
        username = config.get("auth","username")
        password = config.get("auth","password")
    elif config.has_section("creds"):
        username = config.get("creds","username")
        password = config.get("creds","password")
    else:
        logr.error("No credentials found")
        sys.exit()
    endpoint_url = config.get("endpoint", "endpoint_url")
    endpoint_name = config.get("endpoint", "endpoint_name") 
   
    # configure logger 
    log_file_path = config.get("sys","log_file_path")
    logr = logging.getLogger("GnipComplianceLogger")
    rotating_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path + "/%s-log"%endpoint_name,
            mode="a", maxBytes=2**24, backupCount=5)
    rotating_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(funcName)s %(message)s"))
    logr.setLevel(logging.DEBUG)
    #logr.setLevel(logging.ERROR)
    logr.addHandler(rotating_handler)
    
    # processing options
    file_path = config.get("proc", "file_path")

    # configure run mode
    run_args = {}
    if not config.has_option("run", "run_mode"):
        sys.stderr.write('Must configure a "run" block with a "run_mode" parameter\n')
        sys.exit(1)
    
    run_mode = config.get("run", "run_mode")
    
    if run_mode == "one_time":
        if config.has_option("run", "stop_time") and config.has_option("run", "start_time"): 
            run_args["stop_time"] = config.get("run", "stop_time")
            run_args["start_time"] = config.get("run", "start_time") 
            run_args["run_mode"] = run_mode
        else:
            sys.stderr.write('Must configure "start_time" and "stop_time" for "run_mode=one_time"\n')
            sys.exit(1)
    
    elif run_mode == "real_time":
        run_args["run_mode"] = run_mode
        if config.has_option("run", "time_offset_in_seconds") and config.has_option("run", "start_time"):
            sys.stderr.write('Must not set both "time_offset_in_seconds" and "start_time" for "real_time" mode running\n') 
            sys.exit(1)
        if config.has_option("run", "time_offset_in_seconds"):
            run_args["time_offset_in_seconds"] = config.get("run", "time_offset_in_seconds") 
            if int(run_args["time_offset_in_seconds"]) < 300:
                sys.stderr.write("run:time offset must be > 5 minutes")
                sys.exit(1)
        if config.has_option("run", "start_time"):
            run_args["start_time"] = config.get("run", "start_time") 
        
        if config.has_option("run", "query_length_in_seconds"): 
            run_args["query_length"] = config.get("run", "query_length_in_seconds")  
        
        if config.has_option("run", "sleep_time_in_seconds"):
            run_args["sleep_time_in_seconds"] = config.get("run", "sleep_time_in_seconds")
        else:
            run_args["sleep_time_in_seconds"] = 10

    else:
        sys.stderr.write('run_mode mus be "one_time" or "real_time"\n')
        sus.exit(1)

    try:
        compressed = config.getboolean("endpoint", "compressed")
    except ConfigParser.NoOptionError:
        compressed = True
    logr.info("Collection starting for endpoint %s"%(endpoint_url))
    logr.info("Storing data in path %s"%(file_path))
    
    # ok, do it
    client = ComplianceApiClient(endpoint_url
            , endpoint_name
            , username
            , password
            , file_path
            , is_compressed=compressed
    )
    client.run(run_args)

    

