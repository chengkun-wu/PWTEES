import sys, os
from os import walk
from os.path import expanduser

home = expanduser("~")
f = []
corpus = []
opath = "%s/scratch/PWTEES/bo/*-events.tar.gz" % home
ipath = "%s/scratch/PWTEES/bi/" % home 
out = os.popen("ls " + opath)

for file in out.readlines():
	f.append(os.path.basename(file.strip().replace("-events.tar.gz", "")))

out = os.popen("ls " + ipath)

for file in out.readlines():
	corpus.append(os.path.basename(file.strip()))

print set(corpus) - (set(f))

print len(f)
print len(corpus)