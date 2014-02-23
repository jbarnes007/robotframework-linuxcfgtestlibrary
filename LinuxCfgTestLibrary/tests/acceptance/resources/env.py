import os

def get_variables():
    
    variables = {}
    
    variables["ROOT_DIR"] = os.path.abspath(os.path.join(__file__, '..','..')).replace("\\", "/")
    variables["RESOURCES_DIR"] = "/".join((variables["ROOT_DIR"], "resources"))
    variables["ENVIRONMENT_RESOURCES_DIR"] = "/".join((variables["ROOT_DIR"],  "resources", "environments"))
    variables["TEMPLATES_RESOURCES_DIR"] = "/".join((variables["ROOT_DIR"],  "resources", "templates"))

    variables["SSH_USER"] = "tc"
    variables["SSH_PASS"] = "Password@01"
  
    variables['env01'] = "cfgFileTestFile001"
    variables['env02'] = "TestFile1"
    

    
    return variables