import mwparserfromhell, re
from pprint import pprint
from collections import Counter
from math import log
import nltk

class wikisnorkel():
    title = None
    content = None
    wikiobject = None
    categories = []
    externalLinks = []
    internalLinks = []
    most_common = []
    score = -1
    additional_stopwords = ["/ref", "min.", "d", "gb", "nbsp", "the", "wurde", "wurden", "möchte", "möchten", "könnte", "könnten"] #
                            #+ [',', ':', '.', '<', '>', '-', '–', '(', ')', '"', '”', '„', '“','`', '˚' ,'‚', '\'', '‚', '‘', '&', '#', '+', '*', '$', '%', '=' ]
                            # unnecessary, as I've set the minimum length for words to 3

    def __init__(self, title, body):
        self.wikiobject = mwparserfromhell.parse(body)
        self.title = title
        self.content = body
        self.internalLinks = [x.title for x in self.wikiobject.filter_wikilinks()]
        self.externalLinks = [x.title for x in self.wikiobject.filter_external_links()]


    def getScore(self, scoreObject = { } ):
        if self.score >= 0:
            return self.score
        score = 0
        if len(scoreObject) == 0:
            return 0
        if 'base_points' in scoreObject:
            points = scoreObject['base_points']
        else:
            points = 1

        # Points for internal and external links
        if 'external_links_more_than' in scoreObject:
            if len(self.externalLinks) >= scoreObject['external_links_more_than']:
                score += points
        if 'internal_links_more_than' in scoreObject:
            if len(self.internalLinks) >= scoreObject['internal_links_more_than']:
                score += points

        # Points for the number of categories
        if 'categories_more_than' in scoreObject:
            if len(self.categories) >= scoreObject['categories_more_than']:
                score += points

        # Points for entry length
        if 'entry_length' in scoreObject:
            if len(self.content) >= scoreObject['entry_length']:
                score += points

        # Points for appearances. 
        if 'words_in_body' in scoreObject:
            score += self.snorkelForWords(scoreObject['words_in_body'], points)



        self.score = score
        return score

    def snorkelForWords(self, words, points_for_words):
        # The return value should depend on several factors:
        #  - how often is a word in the body?
        #  - is it also in the categories?
        #  - where is the word in the body (the further at the top, the more important)
        # Idea tbd.: Each entry can "earn" 6 times the points:
        #   - 1 for "word is also in one of the categories"
        #   - 1 for word appears in content
        #   - 1 for word count to body length relation is better than XXXXX
        #   - 1 for word count to body length relation is better than XXXXX x 2
        #   - 1 for word appears before the first headline
        #   - 1 if it is amongst the most common words
        returnscore = 0
        
        
        #print(self.title )
            


        if len(words) == 0 or len(self.content) == 0:
            return 0
        for word in words:
            #print(" ==== " + word.lower() + " ====")
            word = word.lower()
            pattern = re.compile(rf'{word}', flags=re.IGNORECASE | re.MULTILINE)
            matches = re.findall(pattern, self.content.lower())
            
            # print(str(len(matches)) + " in content")
            # print(str(len(self.content)) + " content length")

            if len(matches) > 0:
                returnscore += points_for_words
                relation = len(matches) / len(self.content) * 100
                #print(str(relation) + " relation of matches/contentlength")
                if relation > 0.1:
                    returnscore += points_for_words
                if relation > 0.2:
                    returnscore += points_for_words

            match = re.search(pattern, self.content.lower())
            if not match == None and match.start() < 500:
                returnscore += points_for_words
                #print("First match at pos: " + str(match.start()) )

            if len(self.getCategories()) > 0:
                for cat in self.getCategories():
                    if re.search(pattern, cat.lower()):
                        returnscore += points_for_words
                        #print('Also found in categories.')
                        break
            most_common = self.estimateWOrdRelevance() # cool, but veeeeeeeeeeeeeeeery slow
            if len(most_common) > 0 and  word.lower() in most_common:
                #print('Is mongst the 20 most common words in the article!')
                returnscore += points_for_words

        #     print()

        # print(str(returnscore) + " Score")
        # print()
       

            # Ho
        return returnscore

    def getCleanText(self, numbers = False):
        text = self.wikiobject.strip_code().strip()
        my_strip = ["< references / >", "="]
        for ms in my_strip:
            text = text.replace(ms, '')
        my_strip_re = ['<\ ?ref\ ?>[^<]*<\ ?/ref\ ?>', '<\ ?\!--', '--\ ?>']
        for ms in my_strip_re:
            text = re.sub(rf'{ms}', '', text)
        if numbers:
            text = re.sub(rf'[0-9]*', '', text)
        return text
        

    def estimateWOrdRelevance(self):
        if len(self.most_common) > 0:
            return self.most_common
        all_tokens = nltk.word_tokenize(self.getCleanText(True), language='german')
        tokens = []
        stopwords = nltk.corpus.stopwords.words('german') # Remove common German words
        stopwords += self.title.split(" ") + self.additional_stopwords # Remove the name itself and a few chars that somehow get interpreted as words
        for t in all_tokens:
            if not t.lower() in stopwords and len(t) > 2:
                tokens.append(t)
        tf = Counter(tokens)
        freqs = Counter(w.lower() for w in nltk.corpus.brown.words())
        n = len(nltk.corpus.brown.words())
        for word in tf:
            tf[word] *= log(n / (freqs[word] + 1))**2    
        most_common = []
        for word, score in tf.most_common(20):
            most_common.append(word.lower())
            #print('%8.2f %s' % (score, word))
        self.most_common = most_common
        #pprint(self.most_common)
        return most_common

    def getEntryType(self, debug = False):
        # Trying to decide which type an entry is
        # Based on:
        #   - title patterns
        #   - specific headlines in the content
        #   - existence and type of infoboxes
        #   - specific kewords in the content
        # ...
        # Language: DE

        # 1. Criteria of identification: is it a list or a category?
        if "Liste von " in self.title:
            return "list"
        if "Kategorie:" in self.title:
            return "category"   

        # 2. Criteria of identification: if the article has category tags [[Kategorie:xyz]]
        id_criteria = self.getCategories()
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
            #   print(", ".join(id_criteria))
            #   return "person"

            if len(id_criteria) > 1:
                return "%s | %s" % (id_criteria[1], id_criteria[0])
            else:
                return id_criteria[0] # because cat[0] usually is waaaaaaay to specific, I guess we are interested in more general categories

        # 3. Criteria of identification: if the article has an infobox
        id_criteria = self.collectInfoboxes()
        if len(id_criteria) > 0:
            if debug:
                str_id_criteria = ", ".join(id_criteria)
                if len(", ".join(str_id_criteria)) > 120:
                    str_id_criteria = str_id_criteria[:120] + "..."
                print("     - has infoboxes: %s" % (str_id_criteria))
            return id_criteria[0].lower()

        # 4. Criteria of identification: if it is a redirect
        if "#redirect" in self.content.lower() or "#weiterleitung" in self.content.lower() or (len(self.internalLinks) == 1 and len(self.externalLinks)):
            if debug:
                print("     - is probably a redirect with %s wiki and %s external links" % (str(len(self.internalLinks)), str(len(self.externalLinks)))) 
            return "redirect"   

        # 5. Criteria of identification: is it a "ambigious" page?
        if self.isItAnAmbigiousPage():
            return "ambigious page"

        # 6. Criteria of identificaiton: is it some other kind of Wikipedia-internal page?
        if self.title[:len("Wikipedia:")] == "Wikipedia:":
            return "other internal wikipedia page"

        return "unknown"

    def collectInfoboxes(self):
        # Function searches the wiki code for templates of type "Infobox"
        # Not really sure why I did this but the number of infoboxes on a page maybe could be a hint to determine its relevance
        # I guess with this template filter, we could find a lot more interesting things on a wiki page: https://en.wikipedia.org/wiki/Wikipedia:Templates
        # ! Note: Infoboxes are way more common in the English Wikipedia
        #pprint(str(wiki_entry))
        # We're looking for strings like:
        #   [[Wikipedia:Formatvorlage Musikalbum]]
        #   {{Infobox Musikalbum \n'
        # matches = wiki_entry.filter_templates(matches = 'Infobox')       <= this should work ... but somehow doesn't
        resultSet = []
        matches = self.wikiobject.filter_templates(matches = 'Infobox')
        if len(matches) > 0:
            for match in matches:
                infoboxes = re.findall(r"{{Infobox.(.*?)(\n|\\\n|\|)+", str(match), re.M | re.S)
                if len(infoboxes) > 0:
                    for box in infoboxes:
                        box = box[0].strip()
                        if not box in resultSet:
                            resultSet.append(box)

        return resultSet

    def getTitle(self):
        return self.title

    def getContent(self):
        return self.content

    def getWiki(self):
        return self.wikiobject

    def getLinks(self, which):
        if which == "external":
            return self.externalLinks
        if which == "internal":
            return self.internalLinks
        return []

    def matchCategoryAgainstInOrExcludes(self, matchAgainst):
        for category in self.getCategories():
            if category.lower() in [elem.lower() for elem in matchAgainst]:
                return True
        return False

    def getCategories(self):
        if len(self.categories) > 0:
            return self.categories
        # Parse a wiki entry's text to extract categories (if possible)
        # Language: DE
        matches = re.findall(r"\[\[Kategorie:([^\]|]*)[\]|]{1}", self.content)
        if len(matches) == 0:
            return []
        else:
            return matches

    def isItAnAmbigiousPage(self):
        # Check if it's merely a "XYZ can mean the following" type of page
        # Language: DE
        title = self.title
        if re.search(rf"[']+{title}[']+\ssteht\sfür:\s", self.content, re.DOTALL):
            return False
        else:
            return True