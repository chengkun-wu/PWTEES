import os
import types

def getParameterString(combination):
    string = ""
    for key in sorted(combination.keys()):
        if string != "":
            string += "-"
        string += str(key) + "_" + str(combination[key])
    return string

def getArgs(func, args):
    '''Return dictionary without invalid function arguments.'''
    if type(args) == types.DictType:
        argsDict = args
    else:
        argsDict = splitParameters(args)
    validArgs = func.func_code.co_varnames[:func.func_code.co_argcount]
    return dict((key, value) for key, value in argsDict.iteritems() 
                if key in validArgs)

def splitParameters(string):
    if string == None:
        return {}
    if os.path.exists(string): # Read parameters from a file
        f = open(string, "rt")
        string = f.readline().strip()
        f.close()
    paramDict = {}
    paramSets = string.split(";")
    for paramSet in paramSets:
        if ":" in paramSet:
            paramName, paramValueString = paramSet.split(":")
            paramValues = paramValueString.split(",")
            paramDict[paramName] = []
            for value in paramValues:
                try:
                   floatValue = float(value)
                   intValue = int(value)
                   if floatValue != float(intValue):
                       paramDict[paramName].append(floatValue)
                   else:
                       paramDict[paramName].append(intValue)
                except:
                   paramDict[paramName].append(value)
        else:
            paramDict[paramSet] = None 
    return paramDict

def saveParameters(params, output):
    if type(params) == types.StringType:
        params = splitParameters(params)
    f = open(output, "wt")
    paramStrings = []
    for key in sorted(params.keys()):
        paramValues = params[key]
        if type(paramValues) not in [types.TupleType, types.ListType]:
            paramValues = [paramValues]
        paramStrings.append( str(key) + ":" + ",".join([str(x) for x in paramValues]) )
    f.write(";".join(paramStrings))
    f.close()