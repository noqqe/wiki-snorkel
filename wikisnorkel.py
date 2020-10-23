import sys, os, subprocess, mwparserfromhell, wikiparser, xml.sax, yaml, re
from pprint import pprint

debugStopAfterXEntries = 200
#acceptedEntryTypes = ['mann', 'frau', 'person', 'veranstaltung', 'list', 'tier', 'fiktive person']
acceptedEntryTypes = []
onlyGatherCategories = False # for debugging
writeToFile = False # for debugging

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


def collectInfoboxes(wiki_entry):
	# Function searches the wiki code for templates of type "Infobox"
	# Not really sure why I did this but the number of infoboxes on a page maybe could be a hint to determine its relevance
	# I guess with this template filter, we could find a lot more interesting things on a wiki page: https://en.wikipedia.org/wiki/Wikipedia:Templates
	# ! Note: Infoboxes are way more common in the English Wikipedia
	#pprint(str(wiki_entry))
	# We're looking for strings like:
	#	[[Wikipedia:Formatvorlage Musikalbum]]
	#	{{Infobox Musikalbum \n'
	# matches = wiki_entry.filter_templates(matches = 'Infobox')       <= this should work ... but somehow doesn't
	resultSet = []
	matches = wiki_entry.filter_templates(matches = 'Infobox')
	if len(matches) > 0:
		for match in matches:
			infoboxes = re.findall(r"{{Infobox.(.*?)(\n|\\\n|\|)+", str(match), re.M | re.S)
			if len(infoboxes) > 0:
				for box in infoboxes:
					box = box[0].strip()
					if not box in resultSet:
						resultSet.append(box)

	return resultSet


def getCategories(text):
	# Parse a wiki entry's text to extract categories (if possible)
	# Language: DE
	matches = re.findall(r"\[\[Kategorie:([^\]|]*)[\]|]{1}", text)
	if len(matches) == 0:
		return []
	else:
		return matches

def isItAnAmbigiousPage(title, text):
	# Check if it's merely a "XYZ can mean the following" type of page
	# Language: DE
	if re.search(r"[']+{title}[']+\ssteht\sfür:\s", text, re.DOTALL):
		return False
	else:
		return True

def getEntryType(wiki_entry, debug = True):
	# Trying to decide which type an entry is
	# Based on:
	# 	- title patterns
	#	- specific headlines in the content
	# 	- existence and type of infoboxes
	# 	- specific kewords in the content
	# ...
	# Language: DE
	title = wiki_entry[0]
	body = wiki_entry[1]
	wiki = wiki_entry[2]

	# 1. Criteria of identification: is it a list or a category?
	if "Liste von " in title:
		return "list"
	if "Kategorie:" in title:
		return "category"	

	# 2. Criteria of identification: if the article has category tags [[Kategorie:xyz]]
	id_criteria = getCategories(body)
	if len(id_criteria) > 0:
		if debug:
			str_id_criteria = ", ".join(id_criteria)
			if len(", ".join(str_id_criteria)) > 120:
				str_id_criteria = str_id_criteria[:120] + "..."
			print("     - has categories: %s" % str_id_criteria)

		
		# Okay, this is a list of SEARCH TERM => CATEGORY pairs which is checked againgst wikipedia's categories:
		# '*'' is a wildchar character that can be used to match something like "*literatur" (so f.e. "Weltliteratur") 
		# to a "boring stuff" category. In the future, this should be a) safe to use for any edge case or b) overwriteable.
		# 
		# Shit. I just realised, there are way too much categories for a approach like that. Maybe we just focus on the one's we 
		# are actually interested in. 
		ifttt = [
			["Mann", "person"],
			["Frau", "person"],
			["Tag", "day"],
			["Abkürzung", "language stuff"],
			["Sprache", "language stuff"],
			["Partei", "politics"],
			["Produkt", "product"],
			["*literatur", "literature"],
			["Essay", "literature"],
			["Buch", "literature"],
			["Kurzgeschichte", "literature"],
			["Berg in *", "geography"],
			["See in *", "geography"],
			["Welterbstätte in *", "geography"],
			["Fluss *", "geography"],
			["*stadt *", "geography"],
			["Flusssystem in *", "geography"],
			["Senke in *", "geography"],
			["Ort *", "geography"],
			["Region *", "geography"],
			["*region *", "geography"],
			["Gewässer *", "geography"],
			["Bezirk *", "geography"],
			["Gebirge *", "geography"],
			["*gebirge *", "geography"],
		]

		for i in ifttt:
			if "*" in i[0]:
				for idc in id_criteria:
					if i[0].replace("*", "") in idc:
						return i[1]
			else:
				if i[0] in id_criteria:
					return i[1]

		# if " == Leben == " in body or " == Leben und Werk == " in body:
		# 	print(", ".join(id_criteria))
		# 	return "person"

		if len(id_criteria) > 1:
			return "%s | %s" % (id_criteria[1], id_criteria[0])
		else:
			return id_criteria[0] # because cat[0] usually is waaaaaaay to specific, I guess we are interested in more general categories

	# 3. Criteria of identification: if the article has an infobox
	id_criteria = collectInfoboxes(wiki)
	if len(id_criteria) > 0:
		if debug:
			str_id_criteria = ", ".join(id_criteria)
			if len(", ".join(str_id_criteria)) > 120:
				str_id_criteria = str_id_criteria[:120] + "..."
			print("     - has infoboxes: %s" % (str_id_criteria))
		return id_criteria[0].lower()

	# 4. Criteria of identification: if it is a redirect
	wikilinks = [x.title for x in wiki.filter_wikilinks()]
	extlinks = [x.title for x in wiki.filter_external_links()]
	if "#redirect" in body.lower() or "#weiterleitung" in body.lower() or (len(wikilinks) == 1 and len(extlinks)):
		if debug:
			print("     - is probably a redirect with %s wiki and %s external links" % (str(len(wikilinks)), str(len(extlinks)))) 
		return "redirect"	

	# 5. Criteria of identification: is it a "ambigious" page?
	if isItAnAmbigiousPage(title, body):
		return "ambigious page"

	# 6. Criteria of identificaiton: is it some other kind of Wikipedia-internal page?
	if title[:len("Wikipedia:")] == "Wikipedia:":
		return "other internal wikipedia page"
	

	return "unknown"

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
		if (lastEntryIndex != len(handler._pages)-1): 
			lastEntryIndex = (len(handler._pages)-1)

			handler._pages[lastEntryIndex] = [handler._pages[lastEntryIndex][0], 
	    										  handler._pages[lastEntryIndex][1], 
	    										  mwparserfromhell.parse(handler._pages[lastEntryIndex][1]) ] # not exactly sure why I had to rassign 0 and 1, but it works (it's a bit slow though)
	    	
	    	
			if onlyGatherCategories:
				file = open('./categories.txt', 'a')
				for cat in getCategories(handler._pages[lastEntryIndex][1]):
					file.write(cat + "\n")
				file.write("------------ \n")
				file.close()

	    	# Just to print some form of progress to the stdout
			if counter % 50 == 0:
				sys.stdout.write(str(counter))
				sys.stdout.flush()
			counter += 1

			entry_type = getEntryType(handler._pages[lastEntryIndex], False)
			if len(acceptedEntryTypes) == 0 or entry_type.lower() in acceptedEntryTypes:
				if not onlyGatherCategories:
					resultSet.append(handler._pages[lastEntryIndex])
					file = open('./entries.txt', 'a')
					file.write(entry_type + ", " + handler._pages[lastEntryIndex][0] + "\n")
					file.close()
				sys.stdout.write('+')
				sys.stdout.flush()
			else:
				sys.stdout.write('-')
				sys.stdout.flush()
			
			# As we save results in a separate ResultSet, we should reset the handler after each page, right?
			lastEntryIndex = -1;
			handler._pages = [] 

	    
	    #Stop after X articles have been found | only for dev purposes
		if debugStopAfterXEntries > 0 and counter >= debugStopAfterXEntries:
			break




	# This is just my usual development mess for testing and fooling around
	for entry in resultSet:
		if onlyGatherCategories:
			print(entry)
			continue

		print(entry[0])
		print("     - probably of type: %s" % str(getEntryType(entry).upper()))

		wikilinks = [x.title for x in entry[2].filter_wikilinks()]
		extlinks = [x.title for x in entry[2].filter_external_links()]
		print("     - has %s wiki and %s external links" % (str(len(wikilinks)), str(len(extlinks))))
		if len(wikilinks) == 1 and len(extlinks) == 0:
			print("     - probably is a redirect")


		if getEntryType(entry) == "unknown":
			pprint(entry[2])
			exit(0)
			#print(entry[1].strip())
		#print("     - " + getFirstSentence(entry))

			# 	print(" OK => [%s] %s" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))
			# else:
			# 	print("NOK => [%s] %s (skipping)" % (str(lastEntryIndex), handler._pages[lastEntryIndex][0]))


if __name__ == "__main__":
    main()

