#
# Name: postProcessEA.py
#
# Author: Mark Oberfield
#         Meteorological Development Laboratory
#         Office of Science and Technology Integration
#         National Weather Service/NOAA
#
# Purpose: To post-process Enterprise Architect (EA) XML code generation.
#
# Code prerequsites: Python version >2.7 installed on local machine
#
import os, re, sys
try:
    import configparser as cp
except ImportError:
    import ConfigParser as cp
    
import xml.etree.ElementTree as ET
import xmlpp
#
def parseAndGetNameSpaces(fname,References={}):
    #
    events = 'start','start-ns'
    root = None
    ns = {}
    requiredNS = list(References)
    #
    for event, elem in ET.iterparse(fname,events):
        if event == 'start-ns':
            if elem[0] in ns and ns[elem[0]] != elem[1]:
                #
                # NOTE: It is perfectly valid to have the same prefix refer
                #       to different URI namespaces in different parts of the
                #       document. This exception serves as a reminder that
                #       this solution is not robust.
                raise KeyError("Duplicate prefix with different URI found.")
            
            ns[elem[0]] = elem[1]
            
        elif event == 'start' and root == None:
            root = elem
            for prefix, uri in ns.items():
                if prefix not in ['xs','']:
                    root.set('xmlns:%s' % prefix, uri)

                try:
                    requiredNS.pop(requiredNS.index(prefix))
                except ValueError:
                    pass                    

    while True:
        try:
            key = requiredNS.pop()
            uri = References[key].split()[0]
            root.set("xmlns:%s" % key, uri)

        except IndexError:
            break

    return root, ns
    
def fixCodeLists(root,nameSpaces,codeListsDic):
    #
    # Construct attribute string in element
    codeListList=[(x.get('name'),x) for x in root.iterfind('.//xs:element[@type="gml:CodeType"]', nameSpaces)]
    codeListElements = {}

    for key, value in codeListList:
        codeListElements.setdefault(key, []).append(value)
        
    allCodeListNames=list(codeListElements.keys())
    
    for key,value in codeListsDic.items():
        try:
            for m in codeListElements[key]:
                m.attrib['type'] = value
                
            allCodeListNames.pop(allCodeListNames.index(key))
            
        except KeyError:
            print('fixCodeLists: No match for code list KVP: %s,%s' % (key,value))
            
    if len(allCodeListNames) > 0:
        print('fixCodeLists: Unprocessed gml:CodeType(s) in schema: %s' % ' '.join(allCodeListNames))
              
def changeElements(root,nameSpaces,changeDic,attribute):
    #
    # Construct attribute string in element
    searchString = './/xs:element[@%s="%%s"]' % attribute
    for key,value in changeDic.items():
        matches=[x for x in root.iterfind( searchString % key, nameSpaces)]
        if len(matches) == 0:
            print('changeElements: No match for %s: %s,%s' % (attribute,key,value))
        #
        # For any matches found, change the data type attribute
        for m in matches:
            m.attrib[attribute]=value
    
def setNilElements(root,elementList,nameSpaces):

    searchString = './/xs:element[@name="%s"]'
    for elementName in elementList:
        matches=[x for x in root.iterfind( searchString % elementName, nameSpaces)]
        #
        # For any matches found, change the data type attribute
        if len(matches) == 0:
            print('setNilElements: No match for %s' % (elementName))
            
        for m in matches:
            m.attrib['nillable']='true'

def setCommentsForAttributes(root,documentation,nameSpaces):

    for aName, aDocString in documentation.items():
        searchString = './/xs:attribute[@name="%s"]' % aName
        attribute = root.find( searchString, nameSpaces)
        if attribute != None and len(attribute) == 0:
            child = ET.Element('xs:annotation')
            child1 = ET.SubElement(child, 'xs:documentation')
            child1.text = aDocString
            attribute.append(child)
        elif attribute == None:
            print('Missing attribute in schema: %s' % aName)
            
def applyAdjustments(root,adjustmentDic,nameSpaces):

    for action in adjustmentDic:
        searchString = './/xs:element[@%s="%s"]' % (action['kind'],action['value'])
        element = root.find( searchString, nameSpaces)
        for attrbName, attrbValue in zip(action['attributes'].split(','),
                                         action['values'].split(',')):
            element.attrib[attrbName] = attrbValue

def fixBaseExtensions(root,baseExtensionsDic,nameSpaces):
    #
    # Search schema looking for keys
    for key,value in baseExtensionsDic.items():
        matches=[x for x in root.iterfind('.//xs:extension[@base="%s"]'% key, nameSpaces)]
        if len(matches) == 0:
            print('No match for %s' % (key))
        #
        # For any matches found, change the base value
        for m in matches:
            m.attrib['base']=value

def fixIncludes(root,requiredIncludes,nameSpaces):

    extras = []
    #
    # If required includes already present, remove from list
    for element in root.iterfind('.//xs:include', nameSpaces):
        try:
            requiredIncludes.remove(element.attrib.get('schemaLocation'))
        except ValueError:
            extras.append(element)
    #
    # Reuse any extraneous include statements.
    for extra in extras:
        try:
            extra.set('schemaLocation', requiredIncludes.pop(0))
        except IndexError:
            root.remove(extra)
    #
    # Insert the new include statements after any imports and existing include statements
    if len(requiredIncludes):
        for pos, element in enumerate(root):
            if element.tag[-6:] not in ['import', 'nclude']:
                break
            
        for include in requiredIncludes:
            root.insert(pos,ET.Element('{%s}include' % nameSpaces['xs']))
            root[pos].set('schemaLocation', include)
            pos += 1
   
def fixImports(root,requiredImports,nameSpaces):
    #
    # Get import elements already in the document
    importDictionary = {}
    importElements = [(element.get('namespace'),element) for element in root.iterfind('.//xs:import', nameSpaces)]
    
    for element in importElements:
        importDictionary.setdefault(element[0],[]).append(element[1])
    #
    # Mark for removal duplicate imports of the same namespace; only the first one counts
    delQueue = []
    for key, values in importDictionary.items():
        delQueue.extend(values[1:])
    #
    # Set schema location for the namespaces we care about
    notFound = []
    for key, value in requiredImports.items():
        try:
            uri, schemaLocation = value.split()
            element = importDictionary[uri][0]
            element.set('schemaLocation', schemaLocation)

        except KeyError:
            notFound.append(key)
    #
    # If there are missing namespaces that need to be imported, re-use duplicate import statements
    while len(notFound) > 0:
        try:
            element = delQueue.pop(0)
        except IndexError:
            break
        
        key = notFound.pop(0)
        uri, schemaLocation = requiredImports[key].split()
        
        element.set('namespace', uri)
        element.set('schemaLocation', schemaLocation)
        if key not in nameSpaces:
            root.set('xmlns:%s' % key, namespace)            
    #
    # If all needed and required namespaces are imported and there are extra imports, remove them
    if len(notFound) == 0 and len(delQueue) > 0:
        for e in delQueue:
            root.remove(e)
    #                    
    # Otherwise, if there are namespaces that still need to be included
    else:
        # Find where the last import statement is located...
        for insertPoint, element in enumerate(root):
            if element.tag[-6:] != 'import':
                break
            
        while True:
            try:
                key = notFound.pop(0)
            except IndexError:
                break
        
            try:
                new = delQueue.pop()
            except IndexError:
                new = ET.Element('{%s}import' % nameSpaces['xs'])
            
            uri, schemaLocation = requiredImports[key].split()            

            new.set('namespace', uri)
            new.set('schemaLocation', schemaLocation)

            root.insert(insertPoint,new)
            insertPoint += 1
            
            root.set('xmlns:%s' % key, uri)            
    
def removeAbstractMemberTypes(root,nameSpaces,parentChildMap):
    #
    removes = []
    matches=[x for x in root.iterfind('.//xs:extension[@base="gml:AbstractMemberType"]', nameSpaces)]
    #
    for abstractMemberElement in matches:
        #
        # Descend into the tree . . .
        target = abstractMemberElement.find('.//xs:element',nameSpaces)
        try:
            newElementType = '%sPropertyType' % target.attrib.get('ref')
            #
            # Ascend the tree . . .
            parent = parentChildMap[abstractMemberElement]
            while not parent.tag.endswith('element'):
                parent = parentChildMap[parent]
            #
            # Give parent element a new attribute 'type'
            parent.attrib['type'] = newElementType
            #
            # This <complexType> element now slated for removal.
            removes.extend([c for c in parent if c.tag.endswith('complexType')])
            
        except KeyError:
            pass
        
    removeChildren(removes,parentChildMap)

def removeGMLAbstractFeatures(root,nameSpaces,parentChildMap,ignoreElementNames):
    #
    matches=[x for x in root.iterfind('.//xs:element[@substitutionGroup="gml:AbstractFeature"]', nameSpaces)
             if x.get('name') not in ignoreElementNames]
    #
    for x in matches:
        try:
            name = x.get('type').split(':')[1]
        except IndexError:
            name = x.get('type')
            
        target = root.find('.//xs:complexType[@name="%s"]' % name,nameSpaces)
        complexContent = list(target).pop()
        extension = list(complexContent).pop()
        
        if complexContent.tag != '{%s}complexContent' % nameSpaces['xs'] or \
           extension.tag != '{%s}extension' % nameSpaces['xs'] or \
           extension.attrib['base'] != 'gml:AbstractFeatureType':
            continue
        #
        # With these two lines we remove <complexContent> and <extension> elements from the parent "complexType".
        # The children of the <extension> are appended to <complexType> instead, replacing <complexContent>.
        #
        target.remove(complexContent)
        target.extend(list(extension))
        del x.attrib['substitutionGroup']
        
def cleanUpTree(root,nameSpaces,parentChildMap,ignoreElementNames):
    #
    # EA generates code for class objects or instances which we don't want in the final schema.
    badChildren = []    
    for child in root.iterfind('.//xs:element[@name=""]', nameSpaces):
        badChildren.append(child)
    #
    # then remove them.
    removeChildren(badChildren,parentChildMap)
        
    for child in root.iterfind('.//xs:complexType[@name="Type"]', nameSpaces):
        badChildren.append(child)
        
    removeChildren(badChildren,parentChildMap)

    for child in root.iterfind('.//xs:complexType[@name="PropertyType"]', nameSpaces):
        badChildren.append(child)
    removeChildren(badChildren,parentChildMap)
    #
    # EA METCE GML Extension creates a 'gml:defaultCodeSpace' element. Not sure if this is a bug or
    # disagreement w/ Sparx and IWXXM on how CodeLists should be implemented.
    #
    for child in root.iterfind('.//gml:defaultCodeSpace', nameSpaces):
        badChildren.append(child)
    removeChildren(badChildren,parentChildMap)
    #
    # EA METCE GML Extension creates complexTypes with 'ref'.  Remove these.
    removeAbstractMemberTypes(root,nameSpaces,parentChildMap)
    #
    # EA generates a number of elements that inherit from the gml AbstractFeature class. This is
    # unnecessary in most cases.
    removeGMLAbstractFeatures(root,nameSpaces,parentChildMap,ignoreElementNames)
    #
    # Find and remove elements that do not have children, no text nor attributes.
    while True:
        parentChildMap = dict((c,p) for p in root.iter() for c in p)
        empties = []
        for child in root.iter():
            if len(child) == 0:
                if child.attrib == {}:
                    if child.text == None or child.text.strip() == '':
                        empties.append(child)
            else:
                if child.text != None and child.text.strip() == '':
                    child.text = None
            #
            # If we find types with "xs" prefix, remove the prefix.
            if child.attrib.get('type','')[:3] == 'xs:':
                child.attrib['type'] = child.attrib.get('type')[3:]
                
        if len(empties) == 0:
            break
        
        badKeys = removeChildren(empties,parentChildMap)
        for x in badKeys:
            try:
                del(parentChildMap[x])
            except KeyError:
                pass
            
def removeChildren(badChildren,parentChildMap):

    cpy = list(badChildren)
    while True:
        try:
            child = badChildren.pop()
            parentChildMap[child].remove(child)
            
        except KeyError:
            print("Should not happen")
            pass
        
        except IndexError:
            break
        
    return cpy

def main(cfgfile, config):
    
    try:
        config.read(cfgfile)
    except cp.ParsingError:
        parser.error("Requires a valid configuration file: %s", cfgfile)
        return
    
    try:
        basedir = os.getcwd()
        #
        # Assumption: basedir is one directory up from current directory
        EADirectory = config.get('location','EADirectory')
        ReleaseDirectory = config.get('location','ReleaseDirectory')
        
    except cp.NoSectionError as err:
        print(str(err))
        return
        
    EADirFullPath= os.path.join(basedir,EADirectory)            
    ReleaseFullPath = os.path.join(basedir,ReleaseDirectory)
    
    if ord(os.path.sep) != ord('/'):
        EADirFullPath.replace('/',os.path.sep)
        ReleaseFullPath.replace('/',os.path.sep)
        
    DefaultNamespace = config.get('schema','defaultNamespace')
    #
    # Initialization
    schemaFile = config.get('schema','name')
    EASchemaFile = os.path.join(EADirFullPath,schemaFile)
    if not os.path.isfile(EASchemaFile):        
        print('Missing schema file in EA directory, %s' % EASchemaFile )
        return
    #
    outputfile = os.path.join(ReleaseFullPath,schemaFile)
    nameSpaces = root = None
    #
    # Make required changes to EA schema files to be fully compliant.
    # Extract namespace prefixes and URIs in the EA output and check to make sure
    # the mandatory ones are included in the altered, changed schema
    #
    try:
        schemaNamespaces = dict(config.items('imports'))
        root, nameSpaces = parseAndGetNameSpaces(EASchemaFile,schemaNamespaces)
        fixImports(root,schemaNamespaces,nameSpaces)
        
    except cp.NoSectionError:
        root, nameSpaces = parseAndGetNameSpaces(EASchemaFile)
        #
        # If a default namespace is present, then don't process further.
    if "" in nameSpaces:
        return
        
    try:
        includeEntries = [x[1] for x in config.items('includes')]
        fixIncludes(root,includeEntries,nameSpaces)

    except cp.NoSectionError:
        pass

    try:
        ignoreElementNames = config.get('allowedGMLAbstractFeatures','names')
    except cp.NoSectionError:
        ignoreElementNames = []
    #
    # Important dictionary for traversing the EA schema document
    parentChildMap = dict((c,p) for p in root.iter() for c in p)

    #
    # With instance or object diagrams in the Model, lots of cruft is generated as
    # well. Perhaps there's a way to turn this off in EA. The rest of the 'fix' routines
    # are cleaning up residual issues.
    
    cleanUpTree(root,nameSpaces,parentChildMap,ignoreElementNames)
    #
    # Fix elements' types as needed/configured
    try:
        dataTypesDic = dict([tuple(x[1].split()) for x in config.items('dataTypes')])
        changeElements(root,nameSpaces,dataTypesDic,'type')

    except cp.NoSectionError:
        pass
    #
    # Fix elements that refer to code lists
    try:
        codeListsDic = dict(config.items('codeLists'))
        fixCodeLists(root,nameSpaces,codeListsDic)

    except cp.NoSectionError:
        pass
    #
    # Fix substitution groups
    try:
        subGroupsDic = dict(config.items('substitutionGroups'))
        changeElements(root,nameSpaces,subGroupsDic,'substitutionGroup')

    except cp.NoSectionError:
        pass
    #
    # Fix objects that inherit/extend existing GML types
    try:
        baseExtensionsDic = dict(config.items('baseExtensions'))
        fixBaseExtensions(root,baseExtensionsDic,nameSpaces)

    except cp.NoSectionError:
        pass
    #
    # Bug in EA: Does not insert nillable attribute when nillable='true' in EA UML model.
    try:
        nilledElements = config.get('setNilAttribute','names').split(',')
        setNilElements(root,nilledElements,nameSpaces)

    except cp.NoSectionError:
        pass
    #
    # Bug in EA: Attributes' documentation strings are not inserted into schema.
    try:
        attributeDocStringsDic = dict(config.items('attributeDocStrings'))
        setCommentsForAttributes(root,attributeDocStringsDic,nameSpaces)

    except cp.NoSectionError:
        pass
    #
    # One-off for issues than cannot be represented in the UML->XML realization
    try:
        adjustmentDic = [dict(config.items('adjustment%d' % num))
                         for num in range(int(config.get('adjustments','number')))]
        applyAdjustments(root,adjustmentDic,nameSpaces)

    except cp.NoSectionError:
        pass
    #
    # One-off python code instructions for UML->XML realization
    try:
        for cmd in [config.get('addendum%d' % num, 'code')
                    for num in range(int(config.get('addendums','number')))]:
            exec(cmd)

    except cp.NoSectionError:
        pass
    #
    # For some reason EA does not implement tag "attributeFormDefault" as a attribute
    # to the root element, need to add it here.
    #
    if root.get('attributeFormDefault') == None:
        root.set('attributeFormDefault','unqualified')
    #
    # Write out the modified EA schema
    doc = ET.ElementTree(root)
    doc.write(outputfile,xml_declaration=True,encoding="UTF-8",method="xml")        
    del doc
    #
    # EA does not output the default namespace at the moment.  Will set it here.
    ET.register_namespace("", DefaultNamespace)
    #
    # Rewrite to set default namespace
    root, nameSpaces = parseAndGetNameSpaces(outputfile)
    doc = ET.ElementTree(root)    
    doc.write(outputfile,xml_declaration=True,encoding="UTF-8",method="xml")
    del doc
    #
    # Now prettify the schema file
    xmltext = open(outputfile,'r').read()        
    xmlpp.pprint(xmltext.replace('" />','"/>'),open(outputfile,'w'),indent=4)
    xmltext = open(outputfile,'r').read()
    #
    # From stackoverflow 'nbolton'
    textnode_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    prettyXml = textnode_re.sub('>\g<1></',xmltext)
    open(outputfile,'w').write(prettyXml)
    

if __name__ == '__main__':
    #
    config = cp.ConfigParser()
    config.optionxform = str
    if len(sys.argv) == 1:
        print("Usage: %s cfgfile" % sys.argv[0])
    else:
    #
    # Read configuration files for each schema
        for cfgfile in sys.argv[1:]:
            main(cfgfile,config)
