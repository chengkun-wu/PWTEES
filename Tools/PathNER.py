parse__version__ = "$Revision: 1.3 $"

import sys,os
import time, datetime
import sys
import re
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils

import shutil
import subprocess
import tempfile
import codecs

import Utils.Settings as Settings
import Utils.Download as Download
import Tool

def test(progDir):
    return True

def makeEntityElements(beginOffset, endOffset, text, splitNewlines=False, elementName="entity"):
    # NOTE! Entity ids are not set by this function
    # beginOffset and endOffset in interaction XML format
    pathnerOffset = str(beginOffset) + "-" + str(endOffset)
    currentEndOffset = beginOffset
    elements = []
    if splitNewlines:
        entityStrings = text[beginOffset:endOffset+1].split("\n") # TODO should support also other newlines
    else:
        entityStrings = [text[beginOffset:endOffset+1]]
    # Make elements
    currentBeginOffset = beginOffset
    for entityString in entityStrings:
        currentEndOffset += len(entityString)
        if entityString.strip() != "":
            ent = ET.Element(elementName)
            ent.set("id", None) # this should crash the XML writing, if id isn't later redefined
            # Modify offsets to remove leading/trailing whitespace
            entityBeginOffset = currentBeginOffset
            entityEndOffset = currentEndOffset
            if len(entityString.rstrip()) < len(entityString):
                entityEndOffset -= len(entityString) - len(entityString.rstrip())
            if len(entityString.lstrip()) < len(entityString):
                entityBeginOffset += len(entityString) - len(entityString.lstrip())
            # Make the element
            ent.set("charOffset", str(entityBeginOffset) + "-" + str(entityEndOffset))
            if ent.get("charOffset") != pathnerOffset:
                ent.set("origPathNEROffset", pathnerOffset)
            ent.set("type", "Protein")
            ent.set("given", "True")
            ent.set("source", "PathNER")
            ent.set("text", text[entityBeginOffset:entityEndOffset])
            assert ent.get("text") in text, (ent.get("text"), text)
            elements.append(ent)
        currentBeginOffset += len(entityString) + 1 # +1 for the newline
        currentEndOffset += 1 # +1 for the newline
    return elements

def run(input, output=None, elementName="entity", processElement="document", splitNewlines=False, debug=False, pathnerPath=None, trovePath=None):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    if debug:
        print >> sys.stderr, "PathNER work directory at", workdir
    
    infilePath = os.path.join(workdir, "pathner-in.txt")
    infile = codecs.open(infilePath, "wt", "utf-8")
    outfilePath = os.path.join(workdir, "pathner-out.txt")
    idCount = 0

    # Put sentences in dictionary
    sDict = {}
    sentenceHasEntities = {}
    sCount = 0
    for sentence in corpusRoot.getiterator(processElement):
        #infile.write("U" + str(idCount) + " " + sentence.get("text").replace("\n", " ").replace("\n", " ") + "\n")
        infile.write(sentence.get("text").replace("\n", " ").replace("\n", " ") + "\n")
        idCount += 1
        sDict["U" + str(sCount)] = sentence
        sentenceHasEntities["U" + str(sCount)] = False
        sCount += 1

    infile.close()
    
    # Define classpath for java
    if pathnerPath == None:
        pathnerPath = Settings.PATHNER_DIR
    libPath = "/lib/"

    if debug:
        print >> sys.stderr, "Directory of PathNER:", pathnerPath
    pathnerJarPath = pathnerPath + "/PathNER.jar"
    assert os.path.exists(pathnerJarPath), pathnerPath

    classPath = pathnerPath + "/bin"
    classPath += ":" + pathnerPath + libPath + "*"
    
    # Run parser
    print >> sys.stderr, "Running PathNER", pathnerJarPath
    cwd = os.getcwd()
    os.chdir(pathnerPath)

    args = Settings.JAVA.split() + ["-jar", pathnerJarPath, "--test", infilePath, "--output", outfilePath]

    print >> sys.stderr, "PathNER command:", " ".join(args)
    startTime = time.time()
    exitCode = subprocess.call(args)
    assert exitCode == 0, exitCode
    print >> sys.stderr, "PathNER time:", str(datetime.timedelta(seconds=time.time()-startTime))
    os.chdir(cwd)
    
    sentencesWithEntities = 0
    totalEntities = 0
    nonSplitCount = 0
    splitEventCount = 0
    pathnerEntityCount = 0
    removedEntityCount = 0
    
    #Will use a simple method here: read the PathNER results and then do the matching in the sentences
    
    # Read PathNER results
    print >> sys.stderr, "Inserting entities"

    sentenceEntityCount = {}
    #mentionfile = codecs.open(os.path.join(workdir, "file_test_result.txt"), "rt", "utf-8")
    #outfilePath = pathnerPath + "/" + outfilePath
    print >>sys.stderr, 'Getting PathNER results from', outfilePath

    if os.path.isfile(outfilePath): #pathway mentions detected

        mentionfile = codecs.open(outfilePath, "rt", "utf-8")
        menDict = {}
        menSet = set()
        for line in mentionfile:
            #bannerId, offsets, word = line.strip().split("|", 2)
            pathNerTag, mention, pathNerId, confidence = line.strip().split("\t")
            menDict[mention] = pathNerId
            menSet.add(mention)
        mentionfile.close()

        print menSet
        #count for pathway entities
        epCount = 0 
        for sentence in corpusRoot.getiterator(processElement):
            #infile.write("U" + str(idCount) + " " + sentence.get("text").replace("\n", " ").replace("\n", " ") + "\n")
            sentText = sentence.get("text").replace("\n", " ").replace("\n", " ") + "\n"
            startOffsets = []
            endOffsets = []

            bannerEntities = sentence.findall("entity")
            bannerEntityCount = 0

            for bannerEntity in bannerEntities:
                source = bannerEntity.get('source')
                text = bannerEntity.get('text')

                if not source == 'BANNER':
                    print source, text

                bannerEntityCount += 1

            startOffset = 0
            endOffset = 0
            bannerEntity2removed = set()

            for mention in menSet:
                starts = [match.start() for match in re.finditer(re.escape(mention), sentText)]

                #print 'Finding PathNER mention:', mention, starts

                for startOffset in starts:
                    endOffset = startOffset + len(mention)

                    if  startOffset < 0:
                        continue

                    entities = makeEntityElements(int(startOffset), int(endOffset), sentence.get("text"), splitNewlines, elementName)

                    for ent in entities:
                        #Add processing for entities that are overlapped with the PathNER result
                        
                        entOffsets = ent.get("charOffset").split('-')
                        entStart = int(entOffsets[0])
                        entEnd = int(entOffsets[1])

                        for bannerEntity in bannerEntities:
                
                            bannerOffsets = bannerEntity.get('charOffset').split('-')
                            bannerStart = int(bannerOffsets[0])
                            bannerEnd = int(bannerOffsets[1])

                            if debug:
                                print 'PathNER entity:', entStart, entEnd, 'Banner entity:', bannerStart, bannerEnd

                            #Are offsets overlapped or not?
                            if entEnd <= bannerStart or bannerEnd <= entStart: #not overlapped
                                continue
                            else:#overlapped, show remove the banner entity
                                bannerEntity2removed.add(bannerEntity)

                        bannerEntityCount += 1
                        ent.set("id", sentence.get("id") + ".e" + str(bannerEntityCount))
                        epCount += 1

                        sentence.append(ent)
                        pathnerEntityCount += 1
                        
                        if debug:
                            print 'Adding PathNER resutl:', mention
                            print ETUtils.toStr(sentence)
                        
            #Now really to delete the overlapped BANNER entities
            for bEntity in bannerEntity2removed:
                removedEntityCount += 1
                sentence.remove(bEntity)
                
                if debug:
                    print 'Removing entity ', bannerEntity.get('text'), bannerEntity.get('id')
                    print ETUtils.toStr(sentence)

        print >> sys.stderr, "PathNER found", pathnerEntityCount, "entities and remove ", removedEntityCount, " overlapping BANNER entities. "
        print >> sys.stderr, "(" + str(sCount) + " sentences processed)"
        print >> sys.stderr, "New", elementName + "-elements:", totalEntities, "(Split", splitEventCount, "PathNER entities with newlines)"
    
    # Remove work directory
    if not debug:
        shutil.rmtree(workdir)
    else:
        print >> sys.stderr, "PathNER working directory for debugging at", workdir
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
if __name__=="__main__":
    import sys
    
    from optparse import OptionParser, OptionGroup
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="PathNER (pathway mention NER) wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in Interaction XML format", metavar="FILE")
    optparser.add_option("--inputCorpusName", default="PMC11", dest="inputCorpusName", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in Interaction XML format.")
    optparser.add_option("-e", "--elementName", default="entity", dest="elementName", help="PathNER created element tag in Interaction XML")
    optparser.add_option("-p", "--processElement", default="sentence", dest="processElement", help="input element tag (usually \"sentence\" or \"document\")")
    optparser.add_option("-s", "--split", default=False, action="store_true", dest="splitNewlines", help="Split PathNER entities at newlines")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Preserve temporary working directory")
    optparser.add_option("--pathPathNER", default=None, dest="pathPathNER", help="")
    optparser.add_option("--pathTrove", default=None, dest="pathTrove", help="")
    group = OptionGroup(optparser, "Install", "")
    group.add_option("--install", default=None, action="store_true", dest="install", help="Install PathNER")
    group.add_option("--installDir", default=None, dest="installDir", help="Install directory")
    group.add_option("--downloadDir", default=None, dest="downloadDir", help="Install files download directory")
    group.add_option("--javaHome", default=None, dest="javaHome", help="JAVA_HOME setting for ANT, used when compiling PathNER")
    group.add_option("--redownload", default=False, action="store_true", dest="redownload", help="Redownload install files")
    optparser.add_option_group(group)
    (options, args) = optparser.parse_args()
    
    if not options.install:
        if os.path.isdir(options.input) or options.input.endswith(".tar.gz"):
            print >> sys.stderr, "Converting ST-format"
            import STFormat.ConvertXML
            import STFormat.STTools
            options.input = STFormat.ConvertXML.toInteractionXML(STFormat.STTools.loadSet(options.input), options.inputCorpusName)
        print >> sys.stderr, "Running PathNER"
        run(input=options.input, output=options.output, elementName=options.elementName, 
            processElement=options.processElement, splitNewlines=options.splitNewlines, debug=options.debug,
            pathnerPath=options.pathPathNER, trovePath=options.pathTrove)
    else:
        install(options.installDir, options.downloadDir, javaHome=options.javaHome, redownload=options.redownload)
    