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

import os, filecmp
import _utils
from jinja2 import Environment, FileSystemLoader, meta
from robot.libraries.BuiltIn import BuiltIn
from robot.variables import GLOBAL_VARIABLES


class ConfigFileChecker(object):
    robotBuiltIn = BuiltIn()
    
    def _config_file_get_environment_data(self, envVarDir, environment):
        ''' Gets the variables from the environment configuration file for use to build the expected configuration file outputs.
        '''
        environmentDataFilePath = os.path.join(envVarDir, environment) # Create the env data file path
        environmentData = _utils._open_yaml_file(environmentDataFilePath) # Read the environment data from yaml
        
        _utils._myDictAssert(environmentData, 'applicationGroups', ("applicationGroups key not set in file: %s.yaml" % environmentDataFilePath), "ERROR")  # Ensure there is an application Group node in the returned data set
        _utils._myDictAssert(environmentData, 'environment', ("environment key not set in file: %s.yaml" % environmentDataFilePath), "ERROR")  # Ensure there is an environment node in the returned data set
        _utils._myDictAssert(environmentData['environment'], 'auditUsername', ("applicationGroups key not set in file: %s.yaml" % environmentDataFilePath), "ERROR")  # Ensure there is an audit username node in the returned data set
        
        return environmentData # Return the environment data for use

    def _config_file_get_template_data(self, templateDir, applicationGroup):
        ''' The following function will return a dictionary of all the variables for each template that is defined for a specific application group. 
        '''        
        templateFileData = {} # Set up the variable for population
        
        # Gets all the values from the configuration files templates
        for configFileTemplate in self.environmentData['applicationGroups'][applicationGroup]['configurationFiles']:
            configFilePath = os.path.join(templateDir, configFileTemplate)
            
            # Following code will ensure a config file and associated yaml file exists.
            if os.path.exists(configFilePath):
                if os.path.exists(configFilePath + ".yaml"):
                    templateFileData[configFileTemplate] = _utils._open_yaml_file(configFilePath)
                else:
                    raise Exception (("No configuration template is configured for: %s") % (configFilePath))
            else:
                raise Exception (("No configuration file for: %s") % (configFilePath))
            
            _utils._myDictAssert(templateFileData[configFileTemplate], 'configuration', ("Configuration is set for template file: %s.yaml" % configFileTemplate), "ERROR") # Ensure there is configuration node in the returned data
            _utils._myDictAssert(templateFileData[configFileTemplate]['configuration'], 'type', ("No type is set for template file: %s.yaml" % configFileTemplate), "ERROR") # Ensure there is configuration type node in the returned data
    
            configTypeValue = templateFileData[configFileTemplate]['configuration']['type'] # Set the configuration type variable for use
            if configTypeValue not in ("file", "command"):
                raise Exception (("%s is an invalid value for configuration type in file %s. Must be 'file' or 'command'.") % (configTypeValue, configFileTemplate)) # Ensure the set configuration type set is valid
         
            if configTypeValue == "file":
                _utils._myDictAssert(templateFileData[configFileTemplate]['configuration'], 'fileLocation', ("No file location is set for template file: %s.yaml" % configFileTemplate), "ERROR") # Ensure a file location value is set if file type
            
            if configTypeValue == "command":
                _utils._myDictAssert(templateFileData[configFileTemplate]['configuration'], 'command', ("No command is set for template file: %s.yaml" % configFileTemplate), "ERROR") # Ensure a command is set if type is command
            
        return templateFileData # Returns a dict with the variables for each of the configuration files template values.        

    def _config_file_build_check(self, applicationGroup, configFile, server):
        ''' This function will check to ensure all variables in the configuration file have some type of value set.
        '''
        for key in meta.find_undeclared_variables(self.envTemplates.parse # Parse the template data
                                                  (self.envTemplates.loader.get_source # Load the source of the template data
                                                   (self.envTemplates, configFile)[0])):
            
            if key not in self.configurationFileSettings:
                raise Exception (("ERROR: Variable %s not set in configuration file %s for group %s for server %s") % (key, applicationGroup, configFile, server))
    
    def _config_file_build_helper(self, key):
        ''' Configuration file builder helper that adds the contents of environment data dict to the array 
            which is used to build the expected configuration file for comparison.
            
            Class variables used in this function are:
                self.environmentData
                self.configurationFileSettings
        '''
        try:
            for key, value in reduce(dict.get, key.split(":"), self.environmentData).items():
                self.configurationFileSettings[key] = value # Adds the value returned.
        except TypeError:
            pass  # Captures the error and passes as we don't care if there is no value set.
        except AttributeError:
            pass  # Captures the error and passes as we don't care if there is no value set.
    
    def _config_file_build_write(self, generatedFilesPath, configFile, server):
        ''' Writes the generated configuration file to disk.
        '''
        configFileRaw = self.envTemplates.get_template(configFile)
        fileContents = configFileRaw.render(self.configurationFileSettings)
        
        fileContents = fileContents.replace("${ #}", "${#}")
        
        fileLocation = os.path.join(generatedFilesPath, (("%s_%s") % (server, configFile)))
        _utils._write_file(fileLocation, fileContents)
        
    def _config_file_build(self, applicationGroup):
        ''' Builds the expected configuration file or command output for later comparison. 
        '''
        self.configurationFileSettings = {} ## Clears the dictionary for use
        
        # Create the output folder to store the generated files
        generatedFilesPath = _utils._setup_output_folders(os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'], "generatedFiles_%s" % self.environment, applicationGroup))
        if not os.path.exists(generatedFilesPath):
            os.makedirs(generatedFilesPath)
        
        for configFile in self.environmentData['applicationGroups'][applicationGroup]['configurationFiles']:
            # Only run if there are variables to replace in the config file.
            for server in self.environmentData['applicationGroups'][applicationGroup]['servers']:
                self.configurationFileSettings = {} # Clears the dictionary for use
                
                for key, value in self.templateData[configFile].items(): # Adds the variables from the template configuration file to the main settings dict
                    self.configurationFileSettings[key] = value
                
                self._config_file_build_helper(("environment:%s") % (configFile)) # Add the variables from the environment configuration file to the main settings dict
                self._config_file_build_helper(("applicationGroups:%s:%s") % (applicationGroup, configFile))
                self._config_file_build_helper(("applicationGroups:%s:servers:%s:%s") % (applicationGroup, server, configFile))      
                
                self._config_file_build_check(applicationGroup, configFile, server) # Checks to ensure all variables defined in the template have some type of value set.
                self._config_file_build_write(generatedFilesPath, configFile, server) # Writes the generated file
    
        return generatedFilesPath
    
    def _config_file_get_server_files(self, applicationGroup):
        ''' Function that gets the configuration file for diffing or runs the remote command and saves the output to a file.
        '''
        # Create the output folder to store the generated files
        serverFilesPath = _utils._setup_output_folders(os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'], "serverFiles_%s" % self.environment, applicationGroup))
        if not os.path.exists(serverFilesPath):
            os.makedirs(serverFilesPath)
                    
        for configFile in self.environmentData['applicationGroups'][applicationGroup]['configurationFiles']:
            for server in self.environmentData['applicationGroups'][applicationGroup]['servers']:
                
                # Creates the connection to the remote server
                self.robotBuiltIn.run_keyword("Open Connection", server)
                returnValues = self.robotBuiltIn.run_keyword("RSA Get Key Locations")
                self.robotBuiltIn.run_keyword("Login With Public Key", 
                                              self.environmentData['environment']['auditUsername'],
                                              returnValues['privateKey'].replace("/", "\\\\").replace("\\", "\\\\"),
                                              returnValues['privateKeyPass'].replace("/", "\\\\").replace("\\", "\\\\"))

                # Creates the file destination name
                destFileName = os.path.join(serverFilesPath, (("%s_%s") % (server, configFile)))
                
                if self.templateData[configFile]['configuration']['type'] == "file":
                    sourceFileName =  self.templateData[configFile]['configuration']['fileLocation']                
                    returnResult = self.robotBuiltIn.run_keyword_and_ignore_error("Get File", sourceFileName, destFileName.replace("\\", "\\\\"))
                    if returnResult[0] == "FAIL":
                        _utils._result_logger(self.resultFile, server, configFile, "Fail", sourceFileName)
                        raise Exception (("There were no files matching %s on server %s") % (sourceFileName, server))                
                
                if self.templateData[configFile]['configuration']['type'] == "command":
                    cmd = self.templateData[configFile]['configuration']['command']
                    actualResult = self.robotBuiltIn.run_keyword('Execute Command', cmd)
                    _utils._write_file(destFileName, actualResult)
                
                # Disconnect ssh session
                self.robotBuiltIn.run_keyword("Close Connection")

        return serverFilesPath

    def _config_file_compare(self, applicationGroup, generatedFilesPath, serverFilesPath):
        ''' Builds the diff options that have been defined & transverses the directory structure compare the files.
        '''
        for configFile in self.environmentData['applicationGroups'][applicationGroup]['configurationFiles']:
            # Only run if there are variables to replace in the config file.
            if self.templateData[configFile]["configuration"].get('ignore-matching-lines') is not None:
                diffOptions = "-i -w -B --ignore-matching-lines=" + " --ignore-matching-lines=".join(self.templateData[configFile]["configuration"]['ignore-matching-lines'])
            else:
                diffOptions = "-i -w -B"
                
        dc = filecmp.dircmp(generatedFilesPath, serverFilesPath)
        
        for fileCommon in dc.common:
            fileServer = fileCommon.split("_")[0]
            returnResult = self.robotBuiltIn.run_keyword_and_ignore_error("diff_files", os.path.join(generatedFilesPath, fileCommon).replace("\\", "\\\\"), os.path.join(serverFilesPath, fileCommon).replace("\\", "\\\\"), diffOptions)
            if returnResult[0] == "FAIL":
                _utils._result_logger(self.resultFile, fileServer, fileCommon, "Fail", str(returnResult[1]))
                self.robotBuiltIn.log((("Bad news: File %s on server %s with %s") % (fileCommon, fileServer, returnResult[1])), "WARN")
            else:
                _utils._result_logger(self.resultFile, fileServer, fileCommon, "Pass", str(returnResult[1]))
                self.robotBuiltIn.log((("Good news: File %s on server %s with %s") % (fileCommon, fileServer, returnResult[1])), "INFO")
                
    def _main_run_procedure(self, templateDir, applicationGroup):
        ''' Common run procedure that is called from def main().
        '''
        self.templateData = self._config_file_get_template_data(templateDir, applicationGroup) # Gets the template data
        generatedFilesPath = self._config_file_build(applicationGroup) # Builds the expected configuration file based on inputed variables
        serverFilesPath = self._config_file_get_server_files(applicationGroup) # Gets the server file for comparison
        self._config_file_compare(applicationGroup, generatedFilesPath, serverFilesPath) # Compares the generated files with the actual
        
    def main(self, rootDir, envVarDir, templateDir, environment, applicationGroup=None):
        ''' Main procedure that is followed.
        '''
        self.environmentData = self._config_file_get_environment_data(envVarDir, environment) # Gets the environment data for use
        self.environment = environment # Sets the environment variable for use
        self.resultFile = os.path.join(GLOBAL_VARIABLES['${OUTPUTDIR}'], environment + ".csv") # Set up the csv result file output variable
        self.envTemplates = Environment(loader=FileSystemLoader(templateDir)) # Loads the templates for later use to create expected config files
        if applicationGroup == None: # Runs this for all application groups as specified in the passed environment yaml spec file
            for applicationGroup in self.environmentData['applicationGroups']:
                self._main_run_procedure(templateDir, applicationGroup)
        else: # Runs this if a specific application group was requested
                self._main_run_procedure(templateDir, applicationGroup)
    
    if __name__ == "__main__":
        main()