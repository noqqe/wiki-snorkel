import sys, os, subprocess, mwparserfromhell, wikiparser, xml.sax, yaml, re
from pprint import pprint

debugStopAfterXEntries = 50
scoreCriteria = { 
					'prefilter': 
						{ 
							'exclude_patterns' : 
								{ 
									"title": 
										[
											r"^Liste\ ", 
											r"^[0-9]*$"
										], 
									"content": 
										[

										] 
								}, 
							'include_patterns' : { }
						}
				}

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

def isToBeIncludedInFurtherProcessing(wiki_entry, scoreCriteria):
	# Handle pre filtering
	# If include_patterns exist, we process it as kind of a "whitelist"
	# If only exclude_patterns exist, we handle pages against this "blacklist" terms

	# ? TBD: If both exist, we include everything accoring to the include_patterns – 
	#    and from this set exclude everything that matches exclude_patterns ??
	try:
		include_patterns = scoreCriteria['prefilter']['include_patterns']
	except:
		include_patterns = { }
	try:
		exclude_patterns = scoreCriteria['prefilter']['exclude_patterns']
	except:
		exclude_patterns = { }

	if len(include_patterns) > 0:
		for include_pattern in include_patterns["title"]:
			if re.search(include_pattern, wiki_entry[0]):
				return True
		for include_pattern in include_patterns["content"]:
			if re.search(include_pattern, wiki_entry[wiki_entry[2].strip_code().strip()]):
				return True

	elif len(exclude_patterns) > 0:
		for exclude_pattern in exclude_patterns["title"]:
			if re.search(exclude_pattern, wiki_entry[0]):
				return False
		for exclude_pattern in exclude_patterns["content"]:
			if re.search(exclude_pattern, wiki_entry[wiki_entry[2].strip_code().strip()]):
				return False
		return True
	else:
		return True
	

def main():
	# TODO: implement multiple file input
	# TODO: work in batches to keep it managable as one dump 
	#		file can easily contain several million entries

	# Get the dump file
	dump_file = getDumpFile() 

	# Setting up XML dump handler and parser
	handler = wikiparser.WikiXmlHandler()
	parser = xml.sax.make_parser()
	parser.setContentHandler(handler)

	# Setting up control and result variables
	resultSet = []
	lastEntryIndex = -1;

	# Go through dump line by line and collect lines together in handler._pages
	# Each handler._pages represents one wiki entry
	# handler._pages is a one-dimensional array with two elements:
	# 	[0] => Title of wikipedia entry
	# 	[1] => Body of wikipedia entry
	#   [2] => instance of mwparserfromhell | hope we don't run out of memory with this ;-) 
	for line in subprocess.Popen(['bzcat'], 
	                              stdin = open(dump_file), 
	                              stdout = subprocess.PIPE).stdout:
		parser.feed(line)
	    
	    # This checks if we just jumped from the last line of an entry to the new line of the next one – 
	    # thus effectively determining when our parser reaches the end of an entry
		if (lastEntryIndex != len(handler._pages)-1): 
			lastEntryIndex = (len(handler._pages)-1)

			wiki = mwparserfromhell.parse(handler._pages[lastEntryIndex][1]) 
			handler._pages[lastEntryIndex] = [handler._pages[lastEntryIndex][0], 
	    										  handler._pages[lastEntryIndex][1], 
	    										  wiki] # not exactly sure why I had to rassign 0 and 1, but it works (it's a bit slow though)

			if isToBeIncludedInFurtherProcessing(handler._pages[lastEntryIndex], scoreCriteria): 
				resultSet.append(handler._pages[lastEntryIndex])
				print(" OK => [%s] %s" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))
				
			else:
				print("NOK => [%s] %s (skipping)" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))
	    
	    #Stop after X articles have been found | only for dev purposes
		if debugStopAfterXEntries > 0 and len(handler._pages) >= debugStopAfterXEntries:
			break

	# Test mwparserfromhell => https://github.com/earwig/mwparserfromhell
	# wiki = mwparserfromhell.parse(resultSet[len(resultSet)-1][1])
	# wikilinks = [x.title for x in wiki.filter_wikilinks()]
	
	# pprint(wikilinks)
	# pprint(wiki.strip_code().strip())
	pprint(resultSet[len(resultSet)-1][2])


if __name__ == "__main__":
    main()

