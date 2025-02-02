
import os, sys, time

# Note that all XML-RPC methods must be prefixed by confluence1. - to indicate this is version 1 of the API. Atlassian
# reserve the right to introduce another version of the API in the future, and so require the use of the version number
# after "confluence". So a call to the getPage method requires a method name of confluence1.getPage .


class WikiHandler:
    # Helper class to allow easy interaction with the MineStar Confluence Wiki.

    def __init__(self):
        # Either set up a valid login to the wiki, or throw an exception.
        try:
            server   = "http://wiki.minestar.au.cat.com:8081"
            user     = "script"
            password = "script"
            from xmlrpclib import Server
            self.server = Server(server + "/rpc/xmlrpc")
            self.token = self.server.confluence1.login(user, password)
        except Exception, e:
            raise Exception("Couldn't login to the wiki...aborting with exception %s!" % e)

    def getPageByTitle(self, space, pageTitle):
        # Use a page title to retrieve a page from a space. This method returns the full Page object. Space must be the key of 
        # the space, not the space's name. So to retrieve pages for the "Release Management" space, you would use its key 
        # of "release" as the parameter.
        try:
            return self.server.confluence1.getPage(self.token, space, pageTitle)
        except Exception, e:
            raise Exception("Couldn't find a wiki page '%s' in space '%s'...aborting with exception %s!" % (pageTitle, space, e))

    def getPageByID(self, space, pageID):
        # Use a page's ID to retrieve a page from a space. This method returns the full Page object. Space must be the key of 
        # the space, not the space's name. So to retrieve pages for the "Release Management" space, you would use its key 
        # of "release" as the parameter.
        try:
            return self.server.confluence1.getPage(self.token, space, pageID)
        except Exception, e:
            raise Exception("Couldn't find a wiki page with an ID of '%s'...aborting with exception %s!" % (pageID, e))
    
    
    def getPagesForSpace(self, space):
        # Retrieve all pages from a space. This method returns a vector of PageSummaries. Space must be the key of the space, not
        # the space's name. So to retrieve pages for the "Release Management" space, you would use its key of "release" as the 
        # parameter.
        try:
            return self.server.confluence1.getPages(self.token, space)
        except Exception, e:
            raise Exception("Couldn't retrieve pages for space: '%s'...aborting with exception %s!" % (space, e))
    
    
    def storePage(self, page):
        # Write away a page to the wiki. Method will either create or update a page, depending on prior existence. For creating, the 
        # Page given as an argument should have space, title and content fields at a minimum. For updating, the Page given should
        # have id, space, title, content and versions fields at a minimum. The parentId field is always optional. All other fields
        # will be ignored.
        try:
            self.server.confluence1.storePage(self.token, page)
        except Exception, e:
            raise Exception("Couldn't create/update wiki page '%s'...aborting with exception %s!" % (page["title"], e))
    
    
    def getAttachmentsForPage(self, page):
        # Return a vector containing any attachments that are attached to the supplied page.
        try:
            return self.server.confluence1.getAttachments(self.token, page["id"])
        except Exception, e:
            raise Exception("Couldn't retrieve attachments for wiki page '%s'...aborting with exception %s!" % (page["title"], e))
    
    
    def storeAttachment(self, page, attachment, attachmentData):
        # Return a vector containing any attachments that are attached to the supplied page.
        try:
            return self.server.confluence1.addAttachments(self.token, page["id"], attachment, attachmentData)
        except Exception, e:
            raise Exception("Couldn't add attachment '%s' to wiki page '%s'...aborting with error %s!" % (attachment['title'], page["title"], e))
    
    
    def getBlogEntry(self, entryID):
        # Retrieve a single blog entry from the wiki.
        try:
            return self.server.confluence1.getBlogEntry(self.token, entryID)
        except Exception, e:
            raise Exception("Couldn't retrieve blog entry '%s'...aborting with exception %s!" % (blogEntry["title"], e))
    
    
    def getBlogEntries(self, spaceKey):
        # Retrieve all blog entries for a particular space from the wiki.
        try:
            return self.server.confluence1.getBlogEntries(self.token, spaceKey)
        except Exception, e:
            raise Exception("Couldn't retrieve blog entries for space '%s'...aborting with exception %s!" % (spaceKey, e))
    
    
    def storeBlogEntry(self, blogEntry):
        # Write away a blog entry to the wiki. Method will either create or update an entry, depending on prior
        # existence. For creating, the entry given as an argument should have space, title and content fields at a 
        # minimum. For updating, the entry given should have id, space, title, content and versions fields at a 
        # minimum. All other fields will be ignored.
        try:
            return self.server.confluence1.storeBlogEntry(self.token, blogEntry)
        except Exception, e:
            raise Exception("Couldn't create/update blog entry '%s'...aborting with exception %s!" % (blogEntry["title"], e))
    

    def getBlogEntryByTitleAndSpace(self, title, spaceKey):
        # Retrieve a single blog entry from the wiki based on its title and containing space.
        for entrySummary in self.getBlogEntries(spaceKey):
            if str(entrySummary["title"]) == title:
               return self.getBlogEntry(entrySummary["id"])
        return None
     

    def formatMessage(self, message, typeStr):
        # Take a string and format it as a log message.
        if typeStr == "i":
           return "{color:green}INFO    - " + time.strftime("%H:%M:%S, %d-%b-%Y") + " - " + message + "{color}\n"
        if typeStr == "w":
           return "{color:black}WARNING - " + time.strftime("%H:%M:%S, %d-%b-%Y") + " - " + message + "{color}\n"
        if typeStr == "e":
           return "{color:red}*ERROR  - " + time.strftime("%H:%M:%S, %d-%b-%Y") + " - " + message + "*{color}\n"
        return time.strftime("%H:%M:%S, %d-%b-%Y") + " - " + message
     
     
