'''
Created on Apr 5, 2011

@author: William Panting
@dependancies: lxml

This script will read all the tif files in a dir and convert them to jp2 files
it will also write the ocr for the tiffs [pdf and txt output]

@TODO: email integration:waiting on server
'''
from islandoraUtils import converter
from islandoraUtils import fedora_relationships
from islandoraUtils import fileManipulator
from islandoraUtils import misc
import logging, sys, os, time, subprocess, ConfigParser, shutil
from fcrepo.connection import Connection, FedoraConnectionException
from fcrepo.client import FedoraClient 
from lxml import etree

def getConfig():
    '''
    This funciton get all the configuration values for use by the script
    '''
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(os.getcwd(),'UoMScripts','UoM.cfg'))
    global fedoraUrl
    global fedoraUserName
    global fedoraPassword
    global solrUrl
    solrUrl=config.get('Solr','url')
    fedoraUrl=config.get('Fedora','url')
    fedoraUserName=config.get('Fedora', 'username')
    fedoraPassword=config.get('Fedora','password')
    
    
    return True

def startFcrepo():
    '''
helper function that starts up the fedora connection
'''
    connection = Connection(fedoraUrl,
                    username=fedoraUserName,
                     password=fedoraPassword)
    
    global fedora
    try:
        fedora=FedoraClient(connection)
    except FedoraConnectionException:
        logging.error('Error connecting to fedora, exiting'+'\n')
        sys.exit()
    return True

def createBookPDF(bookPath):
    '''
This function creates the pdf of an entire book and ingests it as a DS into fedora
@param pagesDict: the dictionary containing as keys the page number and as values the file path
@param bookPid:  the pid of the book object to add the pdf datastream to
@return bool: true if added false if not 
'''
    #get page to
    bookPath=os.path.join(bookPath,os.path.basename(bookPath)+'.pdf')
    pageNum=1
    while pageNum<=len(pagesDict):
        pagePath=pagesDict[pageNum]
        fileManipulator.appendPDFwithPDF(bookPath, pagePath)
        pageNum+=1         
    
    #create and add pdf datastream
    obj = fedora.getObject(bookPid)
    bookFile=open(bookPath,'rb')
    garbage='smelly'
    try:
        obj.addDataStream(u'PDF', garbage, label=u'PDF',
             mimeType=u'application/pdf', controlGroup=u'M',
             logMessage=u'Added pdf with OCR.')
        logging.info('Added PDF datastream to:'+bookPid)
        ds=obj['PDF']
        ds.setContent(bookFile)
    except FedoraConnectionException:
        logging.exception('Error in adding PDF datastream to:'+bookPid+'\n')
        return False
    return True

def addBookToFedora():
    '''
Helper function that handles creating the book collection obj in fedora
@param modsFilePath: the source of meta data

@return bool: true on function success false on fail
'''
#create the fedora book page object
    global bookPid#global for write to file and use
    bookPid = fedora.getNextPID(u'uofm')
    #bookPid = fedora.getNextPID(u'Awill')
    myLabel=unicode(os.path.basename(os.path.dirname(modsFilePath)))
    obj = fedora.createObject(bookPid, label=myLabel)
   
    #add the book pid to modsFile
    parser = etree.XMLParser(remove_blank_text=True)
    xmlFile = etree.parse(modsFilePath, parser)
    xmlFileRoot = xmlFile.getroot()
    modsElem=etree.Element("{http://www.loc.gov/mods/v3}identifier",type="pid")
    modsElem.text=bookPid
    xmlFileRoot.append(modsElem)
    xmlFile.write(modsFilePath)
    
    #add mods datastream
    modsUrl=open(modsFilePath)
    modsContents=modsUrl.read()
    modsUrl.close()
    try:
        obj.addDataStream(u'MODS', unicode(modsContents), label=u'MODS',
        mimeType=u'text/xml', controlGroup=u'X',
        logMessage=u'Added basic mods meta data.')
        logging.info('Added MODS datastream to:'+bookPid)
    except FedoraConnectionException:
        logging.error('Error in adding MODS datastream to:'+bookPid+'\n')
        
    #add a TN datastream to the object after creating it from the book cover
    tnPath=os.path.join(os.path.dirname(modsFilePath),(myLabel+'_TN.jpg'))
    converter.tif_to_jpg(os.path.join(os.path.dirname(modsFilePath),'0001_a_front_cover.tif'), tnPath,'TN')
    tnUrl=open(tnPath)
    
    try:
        obj.addDataStream(u'TN', u'aTmpStr', label=u'TN',
        mimeType=u'image/jpeg', controlGroup=u'M',
        logMessage=u'Added a jpeg thumbnail.')
        logging.info('Added TN datastream to:'+bookPid)
        ds=obj['TN']
        ds.setContent(tnUrl)
    except FedoraConnectionException as fedoraEX:
        if str(fedoraEX.body).find('is currently being modified by another thread')!=-1:
            logging.warning('Trouble (thread lock) adding TN datastream to: '+bookPid+' retrying.')
            loop=True
            while loop==True:
                loop=False
                try:
                    obj.addDataStream(u'TN', u'aTmpStr', label=u'TN',
                    mimeType=u'image/jpeg', controlGroup=u'M',
                    logMessage=u'Added a jpeg thumbnail.')
                    logging.info('Added TN datastream to:'+bookPid)
                    ds=obj['TN']
                    ds.setContent(tnUrl)
                except FedoraConnectionException as fedoraEXL:
                    if str(fedoraEXL.body).find('is currently being modified by another thread')!=-1:
                        loop=True
                        logging.warning('Trouble (thread lock) adding TN datastream to: '+bookPid+' retrying.')
                    else:
                        logging.error('Error in adding TN datastream to:'+bookPid+'\n')
        else:
            logging.error('Error in adding TN datastream to:'+bookPid+'\n')
    
    #configure rels ext
    objRelsExt=fedora_relationships.rels_ext(obj,fedora_relationships.rels_namespace('fedora-model','info:fedora/fedora-system:def/model#'))
    objRelsExt.addRelationship('isMemberOf','islandora:top')
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('fedora-model','hasModel'),'archiveorg:bookCModel')
    
    try:#trying to handle a bug/feature of locking fedora items
        objRelsExt.update()
    except FedoraConnectionException as fedoraEX:
        if str(fedoraEX.body).find('is currently being modified by another thread')!=-1:
            logging.warning('Trouble (thread lock) updating obj RELS-EXT: '+bookPid+' retrying.')
            loop=True
            while loop==True:
                loop=False
                try:
                    objRelsExt.update()
                except FedoraConnectionException as fedoraEXL:
                    if str(fedoraEXL.body).find('is currently being modified by another thread')!=-1:
                        loop=True
                        logging.warning('Trouble (thread lock) updating obj RELS-EXT: '+bookPid+' retrying.')
                    else:
                        logging.error('Error updating obj RELS-EXT: '+bookPid)
        else:
            logging.error('Error updating obj RELS-EXT: '+bookPid+' retrying.')
            
    #index the book in solr
    sendSolr()
    return True

def addBookPageToFedora(inputTiff, tmpDir):
    '''
Helper function that handles adding and configuring a fedora object for a book page based on the input image and mods file
do i need something separate to add a book collection boj?
@param inputTiff:  the archival data source
@param tmpDir: file directory where non-archeival stuff gets put

@return bool: true on function success false on fail
'''
    #run conversions
    converter.tif_to_jp2(inputTiff,tmpDir,'default','default')
    converter.tif_OCR(inputTiff,tmpDir,{'PDF':'default','Text':'default'})
    
    #determine page number: used for naming
    fullTiffDir=os.path.dirname(inputTiff)
    tifDir=os.path.basename(fullTiffDir)
    tiffName=os.path.basename(inputTiff)
    pageNumber=os.path.basename(inputTiff)
    pageNumber=int(pageNumber[0:pageNumber.index('_')])
    #if front cover
    if tiffName.count('front_cover')==1:
        pageNumber=1
    elif tiffName.count('inner_cover')==1:
        pageNumber=2
    #if it's the inner leaf
    elif tiffName.count('inner_leaf')==1:
        pageNumber=3
    #if back cover
    elif tiffName.count('back_cover')==1:
        #get number of tiff files
        numberOfTiffs=0
        dir=os.path.dirname(inputTiff)
        for file in os.listdir(dir):
            if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff':
                numberOfTiffs+=1
        pageNumber=numberOfTiffs
    #standard a [left side]
    elif tiffName.count('a')==1:
        if pageNumber==1:
            pageNumber=4
        else:
            pageNumber=pageNumber*2+2
    #standard b [right side]
    elif tiffName.count('b')==1:
        if pageNumber==1:
            pageNumber=5
        else:
            pageNumber=pageNumber*2+3
    else:
        logging.error('Bad tiff file name: '+inputTiff+' giving fileNumber: '+str(pageNumber)+'\n')
        return False
    
    logging.info('Working on ingest of page: '+str(pageNumber)+' with source file: '+inputTiff)    

    
    #create the fedora book page object
    pagePid = fedora.getNextPID(u'uofm')
    #pagePid = fedora.getNextPID(u'Awill')
    myLabel=unicode(tifDir+'_Page'+str(pageNumber))
    obj = fedora.createObject(pagePid, label=myLabel)

    #create ingest urls
    if tiffName[(len(tiffName)-4):len(tiffName)]=='.tif':
        tiffNameNoExt=tiffName[0:len(tiffName)-4]
        tifExt='.tif'
    if tiffName[(len(tiffName)-5):len(tiffName)]=='.tiff':
        tiffNameNoExt=tiffName[0:len(tiffName)-5]
        tifExt='.tiff'
    
    baseInUrl=os.path.join(fullTiffDir,tiffNameNoExt)
    baseOutUrl=os.path.join(tmpDir,tiffNameNoExt)
    tiffUrl=open(baseInUrl+tifExt)
    jp2Url=open(baseOutUrl+'.jp2')
    pdfUrl=open(baseOutUrl+'.pdf')
    ocrUrl=open(baseOutUrl+'.txt')
    #this gets the metadata for the page from the tif
    exifPath=baseOutUrl+'.xml'
    converter.exif_to_xml(inputTiff,exifPath)
    exifUrl= open(exifPath)
        
    #this is used for creating the book pdf later
    global pagesDict
    pagesDict[pageNumber]=baseOutUrl+'.pdf'
    

    garbage=u'smelly'
    #tiff datastream
    try:
        obj.addDataStream(u'TIFF', garbage, label=u'TIFF',
             mimeType=u'image/tiff', controlGroup=u'M',
             logMessage=u'Added the archival tiff file.')
        logging.info('Added TIFF datastream to:'+pagePid)
        ds=obj['TIFF']
        ds.setContent(tiffUrl)
    except FedoraConnectionException:
        logging.exception('Error in adding TIFF datastream to:'+pagePid+'\n')
  
    #jp2 datastream
    try:
        obj.addDataStream(u'JP2',garbage, label=u'JP2',
             mimeType=u'image/jp2', controlGroup=u'M',
             logMessage=u'Added jp2 image file.')
        logging.info('Added JP2 datastream to:'+pagePid)
        ds=obj['JP2']
        ds.setContent(jp2Url)
    except FedoraConnectionException:
        logging.exception('Error in adding JP2 datastream to:'+pagePid+'\n')
        
        
    #pdf datastream
    try:
        obj.addDataStream(u'PDF', garbage, label=u'PDF',
             mimeType=u'application/pdf', controlGroup=u'M',
             logMessage=u'Added pdf with OCR.')
        logging.info('Added PDF datastream to:'+pagePid)
        ds=obj['PDF']
        ds.setContent(pdfUrl)
    except FedoraConnectionException:
        logging.exception('Error in adding PDF datastream to:'+pagePid+'\n')
        
        
    #ocr datastream
    try:
        obj.addDataStream(u'OCR', garbage, label=u'OCR',
             mimeType=u'text/plain', controlGroup=u'M',
             logMessage=u'Added basic text of OCR.')
        logging.info('Added OCR datastream to:'+pagePid)
        ds=obj['OCR']
        ds.setContent(ocrUrl)
    except FedoraConnectionException:
        logging.exception('Error in adding OCR Datastream to:'+pagePid+'\n')
        
    #exif datastream
    try:
        obj.addDataStream(u'EXIF', garbage, label=u'EXIF',
             mimeType=u'text/xml', controlGroup=u'M',
             logMessage=u'Added the archival EXIF file.')
        logging.info('Added EXIF datastream to:'+pagePid)
        ds=obj['EXIF']
        ds.setContent(exifUrl)
    except FedoraConnectionException:
        logging.exception('Error in adding EXIF datastream to:'+pagePid+'\n')

    objRelsExt=fedora_relationships.rels_ext(obj,[fedora_relationships.rels_namespace('pageNS','info:islandora/islandora-system:def/pageinfo#'),
                                                  fedora_relationships.rels_namespace('fedora-model','info:fedora/fedora-system:def/model#')])
    objRelsExt.addRelationship('isMemberOf',bookPid)
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('pageNS','isPageNumber'),fedora_relationships.rels_object(str(pageNumber),fedora_relationships.rels_object.LITERAL))
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('fedora-model','hasModel'),'archiveorg:pageCModel')
    
    objRelsExt.update()
    
    #Dynamic Datastreams
    #grab all files that share a name with the tiff and do not use the already used extensions
    dynamicDSList=os.listdir(fullTiffDir)
    
    for dynamicDSFile in os.listdir(fullTiffDir):
        if dynamicDSFile[0:dynamicDSFile.find('.')]!=tiffNameNoExt or (dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.tif' or \
        dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.tiff' or dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.pdf' \
        or dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.jp2' or dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.txt'\
        or dynamicDSFile[dynamicDSFile.find('.'):len(dynamicDSFile)]=='.xml'):
            dynamicDSList.remove(dynamicDSFile)
    #create the dynamic datastreams
    for dynamicDSFile in dynamicDSList:
        dynamicDSFileEXT=dynamicDSFile[dynamicDSFile.find('.')+1:len(dynamicDSFile)]
        dynamicDSFileMimeType=misc.getMimeType(dynamicDSFileEXT)
        dynamicDSFileHandle=open(os.path.join(fullTiffDir,dynamicDSFile),'r')
        try:
            obj.addDataStream(unicode(dynamicDSFileEXT), garbage, label=unicode(dynamicDSFileEXT),
                 mimeType=unicode(dynamicDSFileMimeType), controlGroup=u'M',
                 logMessage=unicode('Added the datastream:'+dynamicDSFileEXT))
            logging.info('Added the datastream: '+dynamicDSFileEXT+' to: '+pagePid)
            ds=obj[dynamicDSFileEXT]
            ds.setContent(dynamicDSFileHandle)
        except FedoraConnectionException:
            logging.exception('Error in adding'+ dynamicDSFileEXT +'datastream to:'+pagePid+'\n')
        
          
    return True

def resumePastOperations():
    '''
Helper function that will finish off the directory that was being worked on during the last run of the script [if there was one]
'''
    #init some necessary values
    inFile=open(resumeFilePath,'r')
    resumeDirIn=''
    resumeDirOut=''
    resumeFiles=[]
    count=0
    
    #figure out what files need to be worked on
    for line in inFile:
        if count==0:
            resumeDirIn=line[0:len(line)-1]
        if count==1:
            resumeDirOut=line[0:len(line)-1]
        if count==2:
            global bookPid
            bookPid=line[0:len(line)-1]
        if count==3:
            global pagesDict
            #eval will let the read in string be treated as inline code to create the dict
            pagesDict=eval(line[0:len(line)-1])
        else:
            resumeFiles.append(line[0:len(line)-1])
        count+=1
    inFile.close()
    #metadata file
    global modsFilePath
    modsFilePath=os.path.join(resumeDirIn,'mods_book.xml')
    #remove that file so that it doesn't get used as a resume point again
    os.remove(resumeFilePath)
    #do that dir
    resumeFilesCopy=resumeFiles#python for loop is not as forgiving as php foreach
    for file in resumeFilesCopy:
        #if it is past 7:30am stop the script and record current state
        currentTime=time.localtime()
        if (currentTime[3]>=7 and currentTime[4]>=30) or currentTime[3]>=8:
            #record state [current directory and files checked already]
            outFile=open(resumeFilePath,'w')
            outFile.write(resumeDirIn+'\n')
            outFile.write(resumeDirOut+'\n')
            outFile.write(bookPid+'\n')
            outFile.write(str(pagesDict)+'\n')
            for fileToWrite in resumeFiles:
                outFile.write(fileToWrite+'\n')
            outFile.close()
            #exit script
            logging.warning('The ingest has stopped for day time activities')
            sys.exit()
            
        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            logging.info('Performing operations on file:'+file)
            addBookPageToFedora(os.path.join(resumeDirIn,file), resumeDirOut)
            
            #remove file that has been operated on so it will not be operated on again on a script resume
        if resumeFiles.count(file)!=0:#fixes a bug where created files were throwing errors
            resumeFiles.remove(file)
    #remove base dir
    createBookPDF(resumeDirOut)
    shutil.rmtree(resumeDirIn)
    shutil.rmtree(resumeDirOut)
    return True

def performOpps():
    '''
go through a directory performing the conversions OCR etc.
'''
    logging.info('MARC file found performing operations.')
    for file in os.listdir(currentDir):
        
        #if it is past 7:30am stop the script and record current state
        currentTime=time.localtime()
        if (currentTime[3]>=7 and currentTime[4]>=30) or currentTime[3]>=8:
            #record state [current directory and files checked already]
            outFile=open(resumeFilePath,'w')
            outFile.write(currentDir+'\n')
            outFile.write(outDir+'\n')
            outFile.write(bookPid+'\n')
            outFile.write(str(pagesDict)+'\n')
            for fileToWrite in fileList:
                outFile.write(fileToWrite+'\n')
            outFile.close()
            #exit script
            logging.warning('The ingest has stopped for day time activities')
            sys.exit()

        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            logging.info('Performing operations on file:'+file)
            addBookPageToFedora(os.path.join(currentDir,file), outDir)
        #remove file that has been operated on so it will not be operated on again on a script resume
        if fileList.count(file)!=0:#fixes a bug where created files were throwing errors
            fileList.remove(file)
    #remove base dir
    createBookPDF(outDir)
    shutil.rmtree(currentDir)
    shutil.rmtree(outDir)
    return True

def sendSolr():
    '''
    This is a helper function that creates and sends information to solr for ingest
    '''
    
    solrFile=os.path.join(os.path.dirname(modsFilePath),'mods_book_solr.xml')
    converter.mods_to_solr(modsFilePath, solrFile)
    solrFileHandle=open(solrFile,'r')
    solrFileContent=solrFileHandle.read()
    solrFileContent=solrFileContent[solrFileContent.index('\n'):len(solrFileContent)]
    curlCall='curl '+solrUrl+'/update?commit=true'+r" -H 'Content-Type: text/xml' --data-binary '"+solrFileContent+r"'"
    r = subprocess.call(curlCall, shell=True)
    if r!=0:
        logging.error('Trouble currling with Solr power. Curl returned code: '+str(r))
    solrFileHandle.close()
    return True
'''
SCRIPT RUN START HERE
'''
if len(sys.argv) == 2:
    sourceDir = sys.argv[1]
    destDir=os.path.join(sourceDir,'islandora')
elif len(sys.argv) == 3:
    sourceDir = sys.argv[1]
    destDir = sys.argv[2]
else:
    print('Please verify source and/or destination directory.')
    sys.exit(-1)
    
#declaration of a dictionary to avoid conditional declaration and syntax ambiguity in assignment/creation
pagesDict={}
sourceDirList = ()#list of directories to be operated on

#add cli,imageMagick to the path and hope for the best [remoove these on production server]
os.environ['PATH']=os.environ["PATH"]+':/usr/local/ABBYY/FREngine-Linux-i686-9.0.0.126675/Samples/Samples/CommandLineInterface'
os.environ['PATH']=os.environ["PATH"]+':/usr/local/Linux-x86-64'
os.environ['PATH']=os.environ["PATH"]+':/usr/local/Exif'
os.environ['PATH']='/usr/local/bin:'+os.environ["PATH"]#need to prepend this one for precedence over pre-existing convert command

#configure logging
logDir=os.path.join(sourceDir,'logs')
if os.path.isdir(logDir)==False:
    os.mkdir(logDir)
logFile=os.path.join(logDir,'UoM_Batch_Controller'+time.strftime('%y_%m_%d')+'.log')
#path for script's internal logging
resumeFilePath=os.path.join(logDir,'BatchControllerState.log')
logging.basicConfig(filename=logFile,level=logging.DEBUG)

#perl script location
marc2mods=os.path.join(os.getcwd(),'UoMScripts','marc2mods.pl')

#config file location
#if the destination directory doesn't exist create it
if os.path.isdir(destDir)==False:
    os.mkdir(destDir)
#start up fedora connection
getConfig()
startFcrepo()

#handle a resume of operations if necessary
if os.path.isfile(resumeFilePath):
    resumePastOperations()

#check and see if source dir is a directory
if os.path.isdir(sourceDir) == False:
    logging.error('Indicated source directory is not a directory.')
    sys.exit(-1)
else:
    #get all directories from sourceDir
    sourceDirList = os.listdir(sourceDir)
# for path in sourceDirList:
    for path in os.listdir(sourceDir):
        if os.path.isdir(os.path.join(sourceDir,path)) == False:
            sourceDirList.remove(path)
#loop through those dirs
for dir in sourceDirList:
    currentDir=os.path.join(sourceDir,dir)
    outDir=os.path.join(destDir,dir)
        
    if os.path.isdir(currentDir):#only run this on a directory
        #get all files from current dir
        fileList = os.listdir(currentDir)
        #loop through those files checking for a marc binary   
        MARC_Check = False
        for file in os.listdir(currentDir):
            if file[file.rindex('.'):len(file)]=='.marc' or file[file.rindex('.'):len(file)]=='.mrc':
                if os.path.isdir(outDir)==False:
                    os.mkdir(outDir)
                MARC_Check=True
                #run Jonathan's perl script here and record the new location of the mods file
                os.chdir(currentDir)
                perlCall=['perl',marc2mods,os.path.join(currentDir,file)]
                subprocess.call(perlCall)
                modsFilePath=os.path.join(currentDir,'mods_book.xml')
                #add book obj to fedora
                addBookToFedora()
                fileList.remove(file)
                break
        #if there was a marc file found file run tif=>ocr, tif=>jp2
        if MARC_Check==True:
            performOpps()