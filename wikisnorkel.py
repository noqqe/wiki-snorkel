import sys, os, subprocess, mwparserfromhell, wikiparser, xml.sax, yaml, re, wikisnorkelclass
from pprint import pprint

debugStopAfterXEntries = 10000
includeEntriesOfType = ['mann', 'frau', 'person', 'veranstaltung', 'list', 'tier', 'fiktive person']
excludeEntriesOfType = []
scoreDefinition = {
	"base_points": 3,
	"external_links_more_than": 10,
	"internal_links_more_than": 10,
	"categories_more_than": 5,
	"entry_length": 1500,
	"words_in_title": [],
	"words_in_body": ['pseudonym', 'regiSseur', 'fiktiv', 'idol', 
					  'pionier', 'betrüger', 'mörder', 'gift', 'heuchler', 
					  'scheinbar', 'welterste', 'rekord', 'bis heute'],
	"words_in_categories": ['gestorben']
}
skipFirst = 0
sep = ";"

def getDumpFile():
	dump_file = ""
	if len(sys.argv) == 1:
		dump_file = input('Please specify dump file: ')
	if len(sys.argv) > 1:
		dump_file = sys.argv[1]
	if not dump_file or os.path.isfile(dump_file) == False:
		print('Invalid wiki dump file path.')
		exit(1)
	return dump_file

def getSaveFile():
	# ! TODO: If save file does exist, read the index of the last entry and ask to continue from there
	save_file = ""
	if len(sys.argv) == 2:
		save_file = input('Please specify save file: ')
	if len(sys.argv) > 2:
		save_file = sys.argv[2]
	if os.path.isfile(save_file) == True:
		print('Save file exists – will append to it.')
	else:
		print('Save file does not exists, creating new one.')
		try:
			f = open(save_file, "w")
			f.write(sep.join(['index', 'title', 'score', 'type', 'categories', 'most relevant words' ]) + "\n")
			f.close()
		except:
			print('Error writing to %s.' % save_file)
			exit(1)
	return save_file

def main():
	# TODO: implement multiple file input
	# TODO: work in batches to keep it managable as one dump 
	#		file can easily contain several million entries

	# Get the dump file
	dump_file = getDumpFile() 
	target_file = getSaveFile()

	# Setting up XML dump handler and parser
	handler = wikiparser.WikiXmlHandler()
	parser = xml.sax.make_parser()
	parser.setContentHandler(handler)

	# Setting up control and result variables
	resultSet = []
	counter = 0;

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
		if (len(handler._pages) == 1): 
			snorkel = wikisnorkelclass.wikisnorkel(handler._pages[0][0], handler._pages[0][1])

			# As we save results in a separate ResultSet, we should reset the handler after each page, right?
			handler._pages = [] 

			# Just to print some form of progress to the stdout
			if counter % 50 == 0:
				sys.stdout.write(str(counter))
				sys.stdout.flush()
			counter += 1

			# Check if we should skip
			if skipFirst > counter:
				sys.stdout.write(".")
				sys.stdout.flush()
				continue

			# Now we need to check, if we want to process this entry further or not.
			# Eight scenarios to check:
			#	case: no categories and no list of exludes  => True (process further)
			#	case: no categories but list of exludes 	=> True
			#	case: categories but no list of excludes	=> True
			#	case: categories and list of exludes 		=> continue if they match, else: True
			#	case: no categories and no list of includes => True
			#	case: no categories but list of includes 	=> continue
			#	case: categories but no list of includes 	=> True
			#	case: categories and list of includes 		=> True if they match, else: continue
			categories = snorkel.getCategories() # multiple categories
			entry_type = snorkel.getEntryType(False) #trying to find a single category

			if len(excludeEntriesOfType) > 0: 	# If no excludeEntries, skip check and proceed
				if len(categories) > 0:			# If no categories to exclude, skip check and proceed
					if snorkel.matchCategoryAgainstInOrExcludes(excludeEntriesOfType):  # If a category matches list of excludes, continue!
						sys.stdout.write("-")
						sys.stdout.flush()
						continue
			elif len(includeEntriesOfType) > 0: # If no includeEntries, skip check and proceed (elif because excluding and including makes no sense?)
				if len(categories) == 0:		# If no categories to include, continue!
					sys.stdout.write("-")
					sys.stdout.flush()
					continue
				else:
					if not snorkel.matchCategoryAgainstInOrExcludes(includeEntriesOfType): # If categories don't match include, continue!
						sys.stdout.write("-")
						sys.stdout.flush()
						continue
			sys.stdout.write("+")
			sys.stdout.flush()

			# Now we can just calculate the score and save it to an output file
			file = open(target_file, 'a')
			file.write(sep.join([
						str(counter), 
						snorkel.getTitle(), 
						str(snorkel.getScore(scoreDefinition)), 
						entry_type, 
						", ".join(categories),
						", ".join(snorkel.estimateWOrdRelevance())
						])  + "\n")
			file.close() 

			if counter == 8:
				exit(0)

			#resultSet.append([title, body, wiki])
	    	
			# file = open('./entries.txt', 'a')
			# file.write(entry_type + ", " + handler._pages[lastEntryIndex][0] + "\n")
			# file.close()

	    
	    #Stop after X articles have been found | only for dev purposes
		if debugStopAfterXEntries > 0 and counter - skipFirst >= debugStopAfterXEntries:
			break




	# This is just my usual development mess for testing and fooling around
	for entry in resultSet:
		pprint(entry)
		# if onlyGatherCategories:
		# 	print(entry)
		# 	continue

		# print(entry[0])
		# print("     - probably of type: %s" % str(getEntryType(entry).upper()))

		# wikilinks = [x.title for x in entry[2].filter_wikilinks()]
		# extlinks = [x.title for x in entry[2].filter_external_links()]
		# print("     - has %s wiki and %s external links" % (str(len(wikilinks)), str(len(extlinks))))
		# if len(wikilinks) == 1 and len(extlinks) == 0:
		# 	print("     - probably is a redirect")


		# if getEntryType(entry) == "unknown":
		# 	pprint(entry[2])
		# 	exit(0)
		# 	#print(entry[1].strip())
		# #print("     - " + getFirstSentence(entry))

		# 	# 	print(" OK => [%s] %s" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))
		# 	# else:
		# 	# 	print("NOK => [%s] %s (skipping)" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))


if __name__ == "__main__":
    main()

