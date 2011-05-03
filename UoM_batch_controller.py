'''
Created on Apr 5, 2011

@author: William Panting
@dependancies: lxml, imageLibDGPY.converter,

This script will read all the tif files in a dir and convert them to jp2 files
it will also write the ocr for the tiffs [pdf and txt output]

TODO: finish fedora book/book page ingest
TODO: kill all files when done
TODO: record current fedora book object on timed end so that book page ingestion can continue
'''
from islandoraUtils import converter
from islandoraUtils import fedora_relationships
import logging, sys, os, time, subprocess, ConfigParser, shutil
from fcrepo.connection import Connection, FedoraConnectionException
from fcrepo.client import FedoraClient 

'''
helper function that starts up the fedora connection
'''
def startFcrepo():
    
    config = ConfigParser.ConfigParser()

    config.read(os.path.join(os.getcwd(),'UoMScripts','UoM.cfg'))
    
    url=config.get('Fedora','url')
    myUserName=config.get('Fedora', 'username')
    myPassword=config.get('Fedora','password')
    connection = Connection(url,
                    username=myUserName,
                     password=myPassword)
    
    global fedora
    try:
        fedora=FedoraClient(connection)
    except FedoraConnectionException:
        logging.error('Error connecting to fedora, exiting'+'\n')
        sys.exit()
    return True

'''
Helper function that handles creating the book collection obj in fedora
@param modsFilePath: the source of meta data

@return bool: true on function success false on fail
'''
def addBookToFedora():
#create the fedora book page object
    global bookPid#global for write to file and use
    bookPid = fedora.getNextPID(u'uofm')
    myLabel=unicode(os.path.basename(os.path.dirname(modsFilePath)))
    obj = fedora.createObject(bookPid, label=myLabel)
    modsUrl=open(modsFilePath)
    garbage=u'smelly'
    
    try:
        obj.addDataStream(u'MODS', garbage, label=u'MODS',
         mimeType=u'text/xml', controlGroup=u'X',
         logMessage=u'Added basic mods meta data.')
        logging.info('Added MODS datastream to:'+bookPid)
        ds=obj['MODS']
        ds.setContent(modsUrl)
    except FedoraConnectionException:
        logging.error('Error in adding MODS datastream to:'+bookPid+'\n')
    
    objRelsExt=fedora_relationships.rels_ext(obj,fedora_relationships.rels_namespace('fedora-model','info:fedora/fedora-system:def/model#'))
    objRelsExt.addRelationship('isMemberOf','islandora:top')
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('fedora-model','hasModel'),'bookCModel')
    objRelsExt.update()
    
    return True
'''
Helper function that handles adding and configuring a fedora object for a book page based on the input image and mods file
do i need something separate to add a book collection boj?
@param inputTiff:  the archival data source
@param modsFilePath: the source of meta data

@return bool: true on function success false on fail
'''
def addBookPageToFedora(inputTiff):    
    #determine page number    #useful for naming
    fullTiffDur=os.path.dirname(inputTiff)
    tifDir=os.path.basename(fullTiffDur)
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
        pageNumber=pageNumber*2+1
    #standard b [right side]
    elif tiffName.count('b')==1:
        if pageNumber==1:
            pageNumber=4
        else:
            pageNumber=pageNumber*2+2
    else:
        logging.error('Bad tiff file name: '+inputTiff+' giving fileNumber: '+str(pageNumber)+'\n')
        return False
    
    logging.info('Working on ingest of page: '+str(pageNumber)+' with source file: '+inputTiff)    
    
    #create the fedora book page object
    pagePid = fedora.getNextPID(u'uofm')
    myLabel=unicode(tifDir+'_Page'+str(pageNumber))
    obj = fedora.createObject(pagePid, label=myLabel)

    #create ingest urls
    if tiffName[(len(tiffName)-4):len(tiffName)]=='.tif':
        tiffNameNoExt=tiffName[0:len(tiffName)-4]
        tifExt='.tif'
    if tiffName[(len(tiffName)-5):len(tiffName)]=='.tiff':
        tiffNameNoExt=tiffName[0:len(tiffName)-5]
        tifExt='.tiff'
    
    baseUrl=fullTiffDur+'/'+tiffNameNoExt
    tiffUrl=open(baseUrl+tifExt)
    jp2Url=open(baseUrl+'.jp2')
    pdfUrl=open(baseUrl+'.pdf')
    ocrUrl=open(baseUrl+'.txt')
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
    
    objRelsExt=fedora_relationships.rels_ext(obj,[fedora_relationships.rels_namespace('pageNS','info:islandora/islandora-system:def/pageinfo#'),
                                                                                    fedora_relationships.rels_namespace('fedora-model','info:fedora/fedora-system:def/model#')])
    objRelsExt.addRelationship('isMemberOf','uofm:'+tifDir)
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('pageNS','isPageNumber'),str(pageNumber))
    objRelsExt.addRelationship(fedora_relationships.rels_predicate('fedora-model','hasModel'),'bookCModel')
    objRelsExt.update()
    
    return True
'''
Helper function that will finish off the directory that was being worked on during the last run of the script [if there was one]
'''
def resumePastOperations():
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
            bookPid=line[0:len(line)-1]
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
    for file in resumeFiles:
        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            logging.info('Performing operations on file:'+file)
            converter.tif_to_jp2(os.path.join(resumeDirIn,file),resumeDirOut,'default','default')
            converter.tif_OCR(os.path.join(resumeDirIn,file),resumeDirOut,{'PDF':'default','Text':'default'})
            shutil.copyfile(os.path.join(resumeDirIn,file), os.path.join(resumeDirOut,file))
            addBookPageToFedora(os.path.join(resumeDirOut,file))
    #remove base dir
    shutil.rmtree(resumeDirIn)
    shutil.rmtree(resumeDirOut)
    return True
'''
go through a directory performing the conversions OCR etc.
'''
def performOpps():
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
            for fileToWrite in fileList:
                outFile.write(fileToWrite+'\n')
            outFile.close()
            #exit script
            logging.warning('The ingest has stopped for day time activities')
            sys.exit()

        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            logging.info('Performing operations on file:'+file)
            converter.tif_to_jp2(os.path.join(currentDir,file),outDir,'default','default')
            converter.tif_OCR(os.path.join(currentDir,file),outDir,{'PDF':'default','Text':'default'})
            shutil.copyfile(os.path.join(currentDir,file), os.path.join(outDir,file))
            addBookPageToFedora(os.path.join(outDir,file))
        #remove file that has been operated on so it will not be operated on again on a script resume
        if fileList.count(file)!=0:#fixes a bug where created files were throwing errors
            fileList.remove(file)
    #remove base dir
    shutil.rmtree(currentDir)
    shutil.rmtree(outDir)
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
    

#add cli,imageMagick to the path and hope for the best
os.environ['PATH']=os.environ["PATH"]+':/usr/local/ABBYY/FREngine-Linux-i686-9.0.0.126675/Samples/Samples/CommandLineInterface'
os.environ['PATH']=os.environ["PATH"]+':/usr/local/Linux-x86-64'

#configure logging
logDir=os.path.join(sourceDir,'logs')
if os.path.isdir(logDir)==False:
    os.mkdir(logDir)
logFile=os.path.join(logDir,'UoM_Batch_Controller'+time.strftime('%y_%m_%d')+'.log')
#path for script's internal logging
resumeFilePath=os.path.join(logDir,'BatchControllerState.log')
logging.basicConfig(filename=logFile,level=logging.DEBUG)

#set cwd 
#os.chdir(MYDIR!!!)
#perl script location
marc2mods=os.path.join(os.getcwd(),'UoMScripts','marc2mods.pl')
#config file location
#if the destination directory doesn't exist create it
if os.path.isdir(destDir)==False:
    os.mkdir(destDir)
#start up fedora connection
startFcrepo()

#handle a resume of operations if necessary
if os.path.isfile(resumeFilePath):
    resumePastOperations()
sourceDirList = ()#list of directories to be operated on

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
                shutil.copyfile(modsFilePath, os.path.join(outDir,'mods_book.xml'))
                modsFilePath=os.path.join(outDir,'mods_book.xml')
                #add book obj to fedora
                addBookToFedora()
                fileList.remove(file)
                break
        #if there was a marc file found file run tif=>ocr, tif=>jp2
        if MARC_Check==True:
            performOpps()