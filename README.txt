@author: William Panting

@dependencies : Kakadu, ABBYY CLI, ImageMagick, Python 2.7, lxml, ConfigParser, islandoraUtils, 
							fcrepo, pypdf perl, MARC::Batch, exiftool, Time::ParseDate
							
							use cpanm for perl modules
							
This script will automate the conversions and Fedora ingestions necessary for UoM
In the script you will need to iether set or remove [if already in system path] the path settings for exiftool, abbyy, imagemagick

The in the UoMScripts directory place a file called UoM.cfg with the following format:

[Fedora]
url:str
username: str
password: str
[Solr]
url:str