#
# Purpose: To 'shepard' changes in UML model to final schema realization for posting
#          to website.  The UML model and the postProcessEA.py program generate the
#          official schemas.
#
# Author: M. Oberfield
#
# Process flow after EA generates the package creating all schemas:
#
#  1) Provide directory listing of EA schemas for further processing
#  2) Run postProcessEA.py on each schema selected by user
#  3) Run comparison tool on changed schema(s) to previous one
#
import configparser as cp
import os
import re
import subprocess
import time
import urllib.error
import urllib.request as ur
import xml.etree.ElementTree as ET

import postProcessEA as pea 

re_range = re.compile(r'(?P<start>\d*)-(?P<end>\d*)')

def listEADirectoryFiles(listingDir='./EA'):

    origWorkingDirectory = os.getcwd()
    try:
        os.chdir(listingDir)
        
    except FileNotFoundError as errmsg:
        
        print(errmsg)
        return None

    preamble = ["\tSchemas in Directory: {}\n".format(os.getcwd())]
    preamble.append("    Modification Time\t\tLength\tName")
    
    eaSchemas = [(f, os.stat(f)) for f in os.listdir('.') if f.endswith('.xsd')]
    os.chdir(origWorkingDirectory)

    print('\n'.join(preamble))

    for num, f in enumerate(eaSchemas):
        print('#{}) {}\t{:>14}\t{}'.format(num+1,
                                             time.strftime('%m/%d/%Y %H:%M %p',
                                                           time.localtime(f[1].st_mtime)),
                                             f[1].st_size,
                                             f[0]))
        
    res = input('\nPlease make your selection(s) [<RET> for none]: ').strip()
    if res == '':
        return []
    #
    # tedious
    sequence = []
    other = []
    for num in res.split(' '):
        if num.isdigit():
            sequence.append(int(num))
        elif num != '':    
            other.append(num.strip())
    
    
    res = ''.join(other)
    other = []
    for num in res.split(','):
        if num.isdigit():
            sequence.append(int(num))
        elif num != '':    
            other.append(num.strip())

    res = ''.join(other)
    other = []
    for r in re_range.findall(res):
        try:
            start = max(1, int(r[0]))
        except TypeError:
            start = 1
            
        try:
            end = min(len(eaSchemas), int(r[1]))
        except TypeError:
            end = len(eaSchemas)

        sequence.extend(range(start, end+1))

    print('\nFollowing schemas are selected for processing:')
    schemas = [eaSchemas[x-1][0] for x in set(sequence)]
    for f in schemas:
        print('\t{}'.format(f))

    res = input('\nProceed? [y/n]: ')
    if 'y' == res.lower()[0]:
        return schemas
    else:
        return []

if __name__ == '__main__':
    
    import sys
    #
    # As EA runs on Windows OS, this is how the root directory is determined.
    HOME = os.environ.get('USERPROFILE')
    #
    try:
        package = sys.argv[1]

    except IndexError:
        print('Missing package name, either "iwxxm-us" or "uswx" argument')
        exit(1)
    #
    # Starting from the HOME directory, build the paths to the schemas' initial
    # and final locations.
    #
    if package == 'iwxxm-us':
        
        REPOSITORY = os.path.join(HOME, 'Repositories', 'iwxxm-us-modelling')
        WEB_STAGING = os.path.join(HOME, 'Schemas', 'IWXXM-US', '3.0')
        
    elif package == 'uswx':

        REPOSITORY = os.path.join(HOME, 'Repositories', 'uswx-modelling')
        WEB_STAGING = os.path.join(HOME, 'Schemas', 'uswx', '2.0')

    else:
        print('Wrong package name, either "iwxxm-us" or "uswx" argument')
        exit(1)
    #
    # Many file comparison apps out there. Pick one that is available to you.
    # Should accept two filenames as command-line arguments.  This program
    # allows me to resolve the differences and save the changed file.
    #
    diffTool = os.path.join(os.environ.get('LOCALAPPDATA'), 'Programs',
                            'Oxygen XML Developer 25', 'diffFiles.exe')

    os.chdir(REPOSITORY)
    schemaFiles = listEADirectoryFiles()
    for schemaFile in schemaFiles:
        #
        # Get all vocabulary entries in schema and verify that the code register(s) exists. (Requires
        # internet access.)
        #
        tree = ET.parse(os.path.join('EA', schemaFile))
        for element in tree.findall('.//vocabulary'):
            try:
                response = ur.urlopen(element.text)
                if response.status != 200:
                    print('{} not reachable ({}). Please investigate.'.format(element.text,
                                                                              response.status))

            except urllib.error.URLError as err_msg:
                print('{} resulted in {}. Please investigate.'.format(element.text, err_msg))
                
        configParser = cp.ConfigParser()
        configParser.optionxform = str
        cfgFile = os.path.join('py', schemaFile.replace('.xsd', '.cfg'))
        
        pea.main(cfgFile, configParser)

        diff_args = [' ', os.path.join(WEB_STAGING, schemaFile),
                     os.path.join(REPOSITORY, 'schemas', schemaFile)]
        #
        # Tool permits comparison, resolution of differences and writing changed schema to
        # the website staging area.
        #
        print(f"Comparing latest {schemaFile} (L) to the newly created one (R)...", flush=True)
        result = subprocess.run(diff_args, executable=diffTool)
