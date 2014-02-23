'''
Copyright 03/01/2014 Jules Barnes

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import os, filecmp, shutil, re
from robot.libraries.BuiltIn import BuiltIn
from jinja2 import Environment, FileSystemLoader, meta
from robot.variables import GLOBAL_VARIABLES
import YamlVariablesLibrary
from YamlVariablesLibrary import _keywords as yvLibKeywords
import _checkerFile

class keywords (object):
    
    def __init__(self, rootDir, envVarDir, templateDir):
        self.robotBuiltIn = BuiltIn()
        self.ybLib = YamlVariablesLibrary.keywords(rootDir, envVarDir)
        self.rootDir = rootDir
        self.envVarDir = envVarDir
        self.templateDir = templateDir
        self.envTemplates = Environment(loader=FileSystemLoader
                                        (templateDir))
        

    def linux_config_check_files(self, environments, applicationGroup=None):
        
        patternRFVar = re.compile(r'''\${(.*?)}''', re.UNICODE|re.VERBOSE|re.S)
        if patternRFVar.search(environments):
            environments = self.robotBuiltIn.get_variable_value(environments)
            environmentList = environments.split(":")
            
            for environment in environmentList:
                _checkerFile.ConfigFileChecker().main(self.rootDir, self.envVarDir, self.templateDir, environment, applicationGroup)
        else:
            _checkerFile.ConfigFileChecker().main(self.rootDir, self.envVarDir, self.templateDir, environments, applicationGroup)
        
    def linux_config_set_variables(self, envConfigFile):

        
        self.envData = (yvLibKeywords._open_yaml_file(os.path.join(self.rootDir, self.envVarDir, envConfigFile)))
        
        self.envGeneratedFilesPath = self._setup_output_folders(os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'], "%s_generatedFiles" % envConfigFile))
        self.envServerFilesPath = self._setup_output_folders(os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'],"%s_serverFiles" % envConfigFile))
        self.resultFileName = ("%s_result.csv" % envConfigFile)
        self.resultFile = self._setup_output_folders(os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'], self.resultFileName))

        os.makedirs(self.envServerFilesPath)
        os.makedirs(self.envGeneratedFilesPath)
        #Global Variables
        #self.envConf = self._set_generic_variables(self.envData['environment']['configuration'])
        #self.envUser = self._set_generic_variables(self.envData['environment']['user'])
        #self.envHomeDir = self._set_generic_variables(self.envData['environment']['homeDir'])
        self.auditUsername = self._set_generic_variables(self.envData['environment']['auditUsername'])       
        self.id = envConfigFile

    def check_environment(self):
        for applicationGroup in self.envData['applicationGroups']:
            self.check_linux_server_commands(applicationGroup)
            for configFileTemplate in self.envData['applicationGroups'][applicationGroup]['configurationFiles']:
                self.check_configuration_file(applicationGroup, configFileTemplate)
        
        self._result_reporter()
        
    def _setup_output_folders(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path) and not os.path.isdir(path):
            os.remove(path)
        return path
            
             
    def _set_generic_variables(self,data):
        try:
            value = data
        except Exception, e:
            self.BuiltIn.log(data,e)
        return value

    def _parse_string_for_variables_helper(self, searchString, varName, varValue):
        searchString = str(searchString)
        if varName in searchString:
            searchString = searchString.replace(varName, varValue)
        return searchString
        
    def _parse_string_for_variables(self, string, applicationGroup=None, server=None):
        string = self._parse_string_for_variables_helper(string,"[homeDir]", self.envHomeDir)
        string = self._parse_string_for_variables_helper(string,"[user]", self.envUser)
        string = self._parse_string_for_variables_helper(string,"[configuration]", self.envConf)
        
        if applicationGroup != None and server != None:
            for varName, varValue in self.envData['applicationGroups'][applicationGroup]['servers'][server].items():
                if varName != "linuxCheckCommands":
                    if not isinstance(varValue, dict):
                        string = string.replace((("[%s]") % (varName)), varValue)
        return string

##################################### CONFIGURATION FILE ######################################################################
    def _get_template_configuration_variables(self, template):
        template_source = self.envTemplates.loader.get_source(self.envTemplates,template)[0]
        parsed_content = self.envTemplates.parse(template_source)
        undeclared_variables = meta.find_undeclared_variables(parsed_content)
        return undeclared_variables

    def _check_template_configuation_dict(self,configFileName,server):
        configFileTemplateVars = self._get_template_configuration_variables(configFileName)
        for key in configFileTemplateVars:
            if key not in self.configurationFileSettings:
                raise Exception (("ERROR: Variable %s not set in configuration file %s for server %s") % (key,configFileName,server))
                return "Error"

    def _render_configuration_file(self, configurationFile, server, configEnvGeneratedFilesPath):
        template = self.envTemplates.get_template(configurationFile)
        fileContents = template.render(self.configurationFileSettings)

        if configurationFile == "setEnv.sh":
            fileContents = fileContents.replace("${ #}", "${#}")
        
        fileName = (("%s_%s_%s") % (server, self.id, configurationFile))
        fileLocation = os.path.join(configEnvGeneratedFilesPath, fileName)
        self.write_file(fileLocation,fileContents)

    def _build_configuration_file_settings(self, key):
        try:
            for key, value in reduce(dict.get, key.split(":"), self.envData).items():
                self.configurationFileSettings[key] = self._parse_string_for_variables(value)
        except AttributeError:
            pass
 
    def build_configuration_file(self, applicationGroup, server, configFileTemplate):
        self.configurationFileSettings = {} ## Clears the dictionary for use

        configEnvGeneratedFilesPath = os.path.join(self.envGeneratedFilesPath, applicationGroup, configFileTemplate)
        if not os.path.exists(configEnvGeneratedFilesPath):
            os.makedirs(configEnvGeneratedFilesPath)
        
        # Process the Template Files Variables
        configTemplateFileVariables = yvLibKeywords._open_yaml_file(os.path.join(self.envTemplatePath, configFileTemplate))
        # Remove the configuration file path for file processing        
        del configTemplateFileVariables["configuration"]
        # Gets the configuration file settings based on the defined environment configuration
        for key, value in configTemplateFileVariables.items():
            self.configurationFileSettings[key] = self._parse_string_for_variables(value[self.envConf])

        self._build_configuration_file_settings(("environment:%s") % (configFileTemplate))
        self._build_configuration_file_settings(("applicationGroups:%s:%s") % (applicationGroup, configFileTemplate))
        self._build_configuration_file_settings(("applicationGroups:%s:servers:%s:%s") % (applicationGroup, server, configFileTemplate))

        returnValue = self._check_template_configuation_dict(configFileTemplate,server)
        if returnValue <> "Error":
            self._render_configuration_file(configFileTemplate, server, configEnvGeneratedFilesPath)
            
        return configEnvGeneratedFilesPath
    
    def check_configuration_file(self, applicationGroup, configFileTemplate):
        
        # Gets and processes the configuration file parameters if one exists.
        if os.path.exists(os.path.join(self.envTemplatePath, configFileTemplate, ".yaml")):
            configTemplateFileVariables = yvLibKeywords._open_yaml_file(os.path.join(self.envTemplatePath, configFileTemplate)) # Getting all the Template File Variables
            configurationType = configTemplateFileVariables["configuration"]["type"] # Find environment type IE Production / Test
        
            # Works if it's a file check or command check
            if configurationType == "file":
                sourceFilePath = configTemplateFileVariables["configuration"]["fileLocation"]
            if configurationType == "command":
                cmd = configTemplateFileVariables["configuration"]["command"]

        # Creates the Server Path folder
        configEnvServerFilesPath = os.path.join(self.envServerFilesPath, applicationGroup, configFileTemplate)
        if not os.path.exists(configEnvServerFilesPath):
            os.makedirs(configEnvServerFilesPath)
        
        for server in self.envData['applicationGroups'][applicationGroup]['servers'].keys():        
            # Remove the configuration file path for file processing    
            configEnvGeneratedFilesPath = self.build_configuration_file(applicationGroup, server, configFileTemplate)          
            self.robotBuiltIn.run_keyword("ssh_connect", server, self.auditUsername)
            fileName = (("%s_%s_%s") % (server, self.id, configFileTemplate))
            destName = os.path.join(configEnvServerFilesPath, fileName)

            if configurationType == "file":
                sourceFile = self._parse_string_for_variables(sourceFilePath, applicationGroup, server)
                returnResult = self.robotBuiltIn.run_keyword_and_ignore_error("ssh_get_file", sourceFile, destName.replace("\\", "\\\\"))
                if returnResult[0] == "FAIL":
                    self._result_logger(server, fileName, "Fail", sourceFile)
                    self.robotBuiltIn.log((("ERROR: Server %s does not have file %s") % (server, sourceFile)), "WARN")
                
            if configurationType == "command":
                actualResult = self.robotBuiltIn.run_keyword('ssh_run_cmd', cmd)
                self.write_file(destName, actualResult)
                
            if configTemplateFileVariables["configuration"].get('ignore-matching-lines') != None:
                diffOpt = "-i -w -B --ignore-matching-lines=" + " --ignore-matching-lines=".join(configTemplateFileVariables["configuration"]['ignore-matching-lines'])
            else:
                diffOpt = "-i -w -B"
                
            self.robotBuiltIn.run_keyword("ssh_disconnect")
            
            
        dc = filecmp.dircmp(configEnvGeneratedFilesPath, configEnvServerFilesPath)
        
        for fileCommon in dc.common:
            fileServer = fileCommon.split("_")[0]
            returnResult = self.robotBuiltIn.run_keyword_and_ignore_error("diff_files", os.path.join(configEnvGeneratedFilesPath, fileCommon).replace("\\", "\\\\"), os.path.join(configEnvServerFilesPath, fileCommon).replace("\\", "\\\\"), diffOpt)
            if returnResult[0] == "FAIL":
                self._result_logger(fileServer, fileCommon, "Fail", str(returnResult[1]))
                self.robotBuiltIn.log((("Bad news: File %s on server %s with %s") % (fileCommon, fileServer, returnResult[1])), "WARN")
            else:
                self._result_logger(fileServer, fileCommon, "Pass", str(returnResult[1]))
                self.robotBuiltIn.log((("Good news: File %s on server %s with %s") % (fileCommon, fileServer, returnResult[1])), "INFO")
                
                    

##################################### Linux Commands ######################################################################           
    def _build_linux_command_list(self, myList, key):
        
        items = reduce(dict.get, key.split(":"), self.envData)
        if items != None:
            for item in items:
                myList.append(item)
        return myList
 
    def build_linux_server_check_list(self, applicationGroup, server):
        self.linuxCheckCommands = yvLibKeywords._open_yaml_file(os.path.join(self.envTemplatePath, "linuxCheckCommands"))
        
        linuxCmdList = [] ## Clears the list for use
        linuxCmdList = self._build_linux_command_list(linuxCmdList, "environment:linuxCheckCommands")
        linuxCmdList = self._build_linux_command_list(linuxCmdList, ("applicationGroups:%s:linuxCheckCommands") % (applicationGroup))
        linuxCmdList = self._build_linux_command_list(linuxCmdList, ("applicationGroups:%s:servers:%s:linuxCheckCommands") % (applicationGroup, server))

        return linuxCmdList     
                
    def check_linux_server_commands(self, applicationGroup):
        for server in self.envData['applicationGroups'][applicationGroup]['servers'].keys():  
            linuxCmdList = self.build_linux_server_check_list(applicationGroup, server)
            self.robotBuiltIn.run_keyword("ssh_connect", server, self.auditUsername)
            for cmdName in linuxCmdList:
                cmd = self.linuxCheckCommands[cmdName]['command']
                cmd = self._parse_string_for_variables(cmd, applicationGroup, server)
                expectedResult = self._parse_string_for_variables(self.linuxCheckCommands[cmdName]['expectedResult'], applicationGroup, server)
                compareOperator = self.linuxCheckCommands[cmdName]['operator']               
                
                actualResult = self.robotBuiltIn.run_keyword('ssh_run_cmd', cmd)

                if self.get_operator_fn(compareOperator)(str(actualResult),str(expectedResult)):
                    msg = (("Good news %s %s %s") % (actualResult, compareOperator, expectedResult))
                    self._result_logger(server, cmdName, "Pass", msg)
                    self.robotBuiltIn.log(msg, "INFO")
                else:
                    msg = (("Bad news: Command %s result was %s which does not %s %s") % (cmd, actualResult, compareOperator, expectedResult))
                    self._result_logger(server, cmdName, "Fail", msg)
                    self.robotBuiltIn.log(msg, "WARN")
            
            self.robotBuiltIn.run_keyword("ssh_disconnect")

    def _result_logger(self, server, auditCheck, result, resultDetails): 
        delimiter = ","
        if not os.path.exists(self.resultFile):
            seq = ("Server", "Audit Check" , "Result", "Result Details")
            fileContents = delimiter.join(seq)
            fileContents += "\n"
            self.write_file(self.resultFile, fileContents)
        else:
            seq = (server, auditCheck, result, resultDetails)
            fileContents = delimiter.join(seq)
            fileContents += "\n"            
            self.file_append(self.resultFile, fileContents)

    def _result_reporter(self):
        csvContents = self.file_csv_read(self.resultFile)
        if 'Fail' in csvContents['Result']:
            self.robotBuiltIn.fail('*HTML* ERROR: See <a href="%s">result.csv</a> & warning messages for test failures' % self.resultFileName)
        else:
            self.robotBuiltIn.pass_execution('*HTML* See <a href="%s">result.csv</a> test results' % self.resultFileName)
            

        