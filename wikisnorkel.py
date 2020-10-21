import sys, os, subprocess, mwparserfromhell
from pprint import pprint

from zimscan import Reader
import wikiparser
import xml.sax

if len(sys.argv) == 1 or not os.path.isfile(sys.argv[1]):
	data_path = '/Volumes/temp/wikidump/sourcefiles/dewiki-latest-pages-articles.xml.bz2' # just for my own dev purposes
else:
	data_path = sys.argv[1]



# Object for handling xml
handler = wikiparser.WikiXmlHandler()
# Parsing object
parser = xml.sax.make_parser()
parser.setContentHandler(handler)
# Iteratively process file
for line in subprocess.Popen(['bzcat'], 
                              stdin = open(data_path), 
                              stdout = subprocess.PIPE).stdout:
    parser.feed(line)
    
    # Stop when 3 articles have been found
    if len(handler._pages) > 2:
        break

pprint(handler._pages[0])



wiki = mwparserfromhell.parse(handler._pages[0][1])
# Find the wikilinks
wikilinks = [x.title for x in wiki.filter_wikilinks()]
pprint(wiki.strip_code().strip())


# with Reader(open(sys.argv[1], 'rb')) as reader:
#     for record in reader:
#         data = record.read()
#         pprint(data)
#         i = i + 1
#         if i == 15:
# 	        exit(0)




