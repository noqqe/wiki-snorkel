import sys, os, subprocess, mwparserfromhell, wikiparser, xml.sax, yaml, re
from pprint import pprint

def getDumpFile():
	dump_file = ""
	if len(sys.argv) == 1:
		dump_file = input('Please specify dump file: ')
	if len(sys.argv) == 2:
		dump_file = sys.argv[1]
	if not dump_file or os.path.isfile(dump_file) == False:
		print('Invalid wiki dump file path.')
		exit(1)
	return dump_file

def isToBeIncludedInFurtherProcessing(entry, scoreCriteria):
	# Handle pre filtering
	return True

def main():
	# Get the dump file
	# TODO: implement multiple file input
	dump_file = getDumpFile()
	#scoreCriteria = getScoreCriteria()
	scoreCriteria = False

	# Setting up XML dump handler and parser
	handler = wikiparser.WikiXmlHandler()
	parser = xml.sax.make_parser()
	parser.setContentHandler(handler)

	# Setting up control and result variables
	resultSet = []
	lastEntryIndex = -1;
	debugStopAfterXEntries = 100

	# Go through dump line by line and collect lines together in handler._pages
	# Each handler._pages represents one wiki entry
	# handler._pages is a one-dimensional array with two elements:
	# 	[0] => Title of wikipedia entry
	# 	[1] => Body of wikipedia entry
	for line in subprocess.Popen(['bzcat'], 
	                              stdin = open(dump_file), 
	                              stdout = subprocess.PIPE).stdout:
	    parser.feed(line)
	    
	    # This checks if we just jumped from the last line of an entry to the new line of the next one – 
	    # thus effectively determining when our parser reaches the end of an entry
	    if (lastEntryIndex != len(handler._pages)-1): 
	    	lastEntryIndex = (len(handler._pages)-1)

	    	if isToBeIncludedInFurtherProcessing(handler._pages[lastEntryIndex], scoreCriteria): 
	    		resultSet.append(handler._pages[len(handler._pages)-1])
	    		print(" OK => %s. %s" % (str(len(handler._pages)-1), handler._pages[lastEntryIndex][0]))
	    	else:
	    		print("NOK => %s. %s (skipping)" % (str(len(handler._pages)-1), handler._pages[lastEntryIndex][0]))
	    
	    #Stop after X articles have been found | only for dev purposes
	    if len(handler._pages) >= debugStopAfterXEntries:
	        break

	# Test mwparserfromhell => https://github.com/earwig/mwparserfromhell
	wiki = mwparserfromhell.parse(resultSet[99][1])
	wikilinks = [x.title for x in wiki.filter_wikilinks()]
	
	pprint(wikilinks)
	pprint(wiki.strip_code().strip())



if __name__ == "__main__":
    main()

