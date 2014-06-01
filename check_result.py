import sys, os
from os import walk
from os.path import expanduser

#home = expanduser("~")
f = []
corpus = []
opath = "bo/*-events.tar.gz"
ipath = "bi/*.txt"
out = os.popen("ls " + opath)

for file in out.readlines():
	f.append(os.path.basename(file.strip().replace("-events.tar.gz", "")).replace(".txt", ""))

out = os.popen("ls " + ipath)

for file in out.readlines():
	corpus.append(os.path.basename(file.strip()).replace(".txt", ""))


#print len(f)
#print len(corpus)

if len(f) == len(corpus):
	print >> sys.stderr, 'All input files have been successfully processed!'
else:
	print >> sys.stderr, 'Failed to generate events for some of the files!'
	
	for pmid in set(corpus) - (set(f)):  
		print pmid	
