import sys, os
import types
#import uuid
import subprocess
from ClusterConnection import ClusterConnection
import re
import codecs

SGEJobTemplate = """#!/bin/bash
#$ -S /bin/bash
#$ -cwd
#$ -V
##$ -pe smp.pe 2
#as serial, don't specify -pe  

#output dirs
#$ -o log/
#$ -e err/
#$ -l twoday
##$ -t 1-20

%commands

"""


class SGEConnection(ClusterConnection):
    """
    For using the batch system, Sun Grid Engine (SGE).
    """
    def __init__(self, account=None, workdir=None, settings=None, wallTime=None, memory=None, cores=None, modules=None, preamble=None, debug=False):
        if wallTime == None:
            wallTime = "48:00:00"
        if memory == None:
            memory = 4000
        #if modules == None:
        #    modules = ["python", "ruby"]
        ClusterConnection.__init__(self, account=account, workdir=workdir, settings=settings, memory=memory, cores=cores, modules=modules, wallTime=wallTime, preamble=preamble, debug=debug)
        self.submitCommand = "qsub"
        self.jobListCommand = "qstat"
        self.jobTemplate = SGEJobTemplate

    def submit(self, script=None, jobDir=None, jobName=None, stdout=None, stderr=None):
        pstdout, pstderr = ClusterConnection.submit(self, script, jobDir, jobName, stdout, stderr)
        if pstderr != None:
            print >> sys.stderr, pstderr
        print >> sys.stderr, pstdout
        assert pstdout.startswith("Your job "), pstdout
        #Use regular expression to find the job id
        searchObj = re.search( r'[0-9]+ \(', pstdout)
        print pstdout

        jobId = ''
        if searchObj:
            jobId = searchObj.group()[:-2]
        else:
            print >> sys.stderr, 'Error in parsing the SGE job id!'

        return self._writeJobFile(jobDir, jobName, {"SGEID":jobId}, append=True)
    

    def getJobStatus(self, job):
        jobAttr = self._readJobFile(job)
        # Check whether job exists
        if jobAttr == None:
            return None
        if "SGEID" not in jobAttr:
            return "FAILED" # submitting the job failed

        #the details of the job
        jobStatLines = self.run(self.jobListCommand)

        if jobStatLines:
            for line in jobStatLines:
                line = line.strip()
                splits = line.split()

                if splits[0] == jobAttr["SGEID"]:
                    if self.debug:
                        print >> sys.stderr, "SGE: ", line

                    if splits[4].startswith("q"):
                        return "QUEUED"

                    if splits[4].startswith("e"):
                        return "FAILED"

                    if splits[4].startswith("r"):
                        return "RUNNING"

        else:
            return "FINISHED"

        return "FAILED"
