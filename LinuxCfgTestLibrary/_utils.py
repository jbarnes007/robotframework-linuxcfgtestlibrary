'''
Created on 11/01/2014

@author: Jules Barnes
'''

import yaml, os, shutil, csv
from robot.libraries.BuiltIn import BuiltIn

def _open_yaml_file(fileName):
    try:
        fileName += ".yaml"
        f = open(fileName)
    except IOError:
        raise Exception (("Unable to open %s") % (fileName))
    fileContents = yaml.safe_load(f) # use safe_load instead load
    f.close()
    return fileContents

def _myDictAssert(dictData, dictKey, message, level="INFO"):
    
    if dictData.get(dictKey) is None:
        if level == "ERROR":
            raise Exception(message)
        else:
            BuiltIn().log(message, level)
 
def _setup_output_folders(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path) and not os.path.isdir(path):
        os.remove(path)
    return path

def _write_file(fileName, fileContents):
    fo = open(fileName, "wb")
    BuiltIn().log((("Writing File: %s") % (fileName)), "INFO")
    fo.write(fileContents)
    fo.close()
    
def _file_append(fileName, fileContents):
    fo = open(fileName, "ab")
    BuiltIn().log((("Appending to File: %s") % (fileName)), "INFO")
    fo.write(fileContents)

def _file_csv_read(csvFileName):
    f = open(csvFileName, 'rU')
    reader = csv.reader(f)
    headers = reader.next()
    column = {}
    for h in headers:
        column[h] = []
    for row in reader:
        for h, v in zip(headers, row):
            column[h].append(v)
    
    return column 
    
def _result_logger(resultFile, server, auditCheck, result, resultDetails): 
    delimiter = ","
    if not os.path.exists(resultFile):
        seq = ("Server", "Audit Check" , "Result", "Result Details")
        fileContents = delimiter.join(seq)
        fileContents += "\n"
        _write_file(resultFile, fileContents)
    else:
        seq = (server, auditCheck, result, resultDetails)
        fileContents = delimiter.join(seq)
        fileContents += "\n"            
        _file_append(resultFile, fileContents)

def _result_reporter(resultFile):
    csvContents = _file_csv_read(resultFile)
    if 'Fail' in csvContents['Result']:
        BuiltIn().fail('*HTML* ERROR: See <a href="%s">result.csv</a> & warning messages for test failures' % resultFile)
    else:
        BuiltIn().pass_execution('*HTML* See <a href="%s">result.csv</a> test results' % resultFile)    