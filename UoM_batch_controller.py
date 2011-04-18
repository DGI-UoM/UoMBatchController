'''
Created on Apr 5, 2011

@author: William Panting
@dependancies: lxml, imageLibDGPY.converter,

This script will read all the tif files in a dir and convert them to jp2 files
it will also write the ocr for the tiffs [pdf and txt output]

TODO: put in stop time
TODO: put in state recording and resume
'''
from islandoraUtils import converter
import logging, sys, os, time
'''
Helper function that will finish off the directory that was being worked on during the last run of the script [if there was one]
'''
def resumePastOperations():
    inFile=open(resumeFilePath,'r')
    resumeDirIn=''
    resumeDirOut=''
    resumeFiles=[]
    count=0
    for line in inFile:
        if count==0:
            resumeDirIn=line[0:len(line)-1]
        if count==1:
            resumeDirOut=line[0:len(line)-1]
        else:
            resumeFiles.append(line[0:len(line)-1])
        count+=1
    inFile.close()
    #remove that file so that it doesn't get used as a resume point again
    os.remove(resumeFilePath)
    #do that dir
    for file in resumeFiles:
        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            if os.path.isdir(resumeDirOut)==False:
                os.mkdir(resumeDirOut)
            converter.tif_to_jp2(os.path.join(resumeDirIn,file),resumeDirOut,'default','default')
            #converter.tif_OCR(os.path.join(resumeDirIn,file),resumeDirOut,{'PDF':'default','Text':'default'})
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
            for fileToWrite in fileList:
                outFile.write(fileToWrite+'\n')
            outFile.close()
            #exit script
            logging.warning('The injest has stopped for day time activities')
            sys.exit()

        if file[(len(file)-4):len(file)]=='.tif' or file[(len(file)-5):len(file)]=='.tiff' :
            if os.path.isdir(outDir)==False:
                os.mkdir(outDir)
            converter.tif_to_jp2(os.path.join(currentDir,file),outDir,'default','default')
            #converter.tif_OCR(os.path.join(currentDir,file),outDir,{'PDF':'default','Text':'default'})
        #remove file that has been operated on so it will not be operated on again on a script resume
        if fileList.count(file)!=0:#fixes a bug where created files were throwing errors
            fileList.remove(file)
    return True
'''
SCRIPT RUN START HERE
'''
if len(sys.argv) == 2:
    sourceDir = sys.argv[1]
    destDir=os.path.join(surceDir,'islandora')
elif len(sys.argv) == 3:
    sourceDir = sys.argv[1]
    destDir = sys.argv[2]
else:
    print('Please verify source and/or destination directory.')
    sys.exit(-1)
    
#configure logging
logDir=os.path.join(sourceDir,'logs')
if os.path.isdir(logDir)==False:
    os.mkdir(logDir)
#logFile=os.path.join(os.getcwd(),'UoM_Batch_Controller'+time.strftime('%y_%m_%d')+'.log')
logFile=os.path.join(logDir,'UoM_Batch_Controller'+time.strftime('%y_%m_%d')+'.log')
#path for script's internal logging
resumeFilePath=os.path.join(logDir,'BatchControllerState.log')
logging.basicConfig(filename=logFile,level=logging.DEBUG)
    
#handle a resume of operations if necessary
if os.path.isfile(resumeFilePath):
    resumePastOperations()
    
sourceDirList = ()#list of directories to be operated on
#add cli to the path and hope for the best
os.environ['PATH']=os.environ["PATH"]+':/usr/local/ABBYY/FREngine-Linux-i686-9.0.0.126675/Samples/Samples/CommandLineInterface'
#check and see if source dir is a directory
if os.path.isdir(sourceDir) == False:
    logging.error('Indicated source directory is not a directory.')
    sys.exit(-1)
else:
    #get all directories from sourceDir
    sourceDirList = os.listdir(sourceDir)
# for path in sourceDirList:
    for path in os.listdir(sourceDir):
        if os.path.isdir(sourceDir + '/' + path) == False:
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
                MARC_Check=True
                #run Jonathan's perl script here
                #change the extension of the marc file so that this directory is not used again 
                #TODO: refactor on release to remove all files
                fileList.remove(file)
                os.rename(os.path.join(currentDir, file),os.path.join(currentDir,file+'.dun'))
                break
        #if there was a marc file found file run tif=>ocr, tif=>jp2
        if MARC_Check==True:
            performOpps()