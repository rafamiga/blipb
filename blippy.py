# blippy - a library used to communicate with blip.pl API
#
#  Copyright (C) 2008 Patryk Bajer, http://blippy.sourceforge.net
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import httplib
import cjson
import base64
import exceptions
import random
import mimetypes
import threading
from exceptions import Exception
from Queue import Queue

BLIPPY_VERSION = "0.1.4"
JSON = "application/json"
BLIP_API_VERSION = "0.02"
BLIP_API_URL = "api.blip.pl"
USER_AGENT = "Blippy/"+BLIPPY_VERSION

class BadOperationException(Exception):
    def __init__(self, args):
        self.args = (args,)

class ServerBusyException(Exception):
    def __init__(self):
        self.args = ("Server is busy. Try again later",)

class BadCredentialsException(Exception):
    def __init__(self):
        self.args = ("User must be authenticated",)

class BadArgumentsException(Exception):
    def __init__(self):
        self.args = ("Invalid arguments for request",)

class NotFoundException(Exception):
    def __init__(self):
        self.args = ("Can't find resource you requested for or invalid URL",)

class Communicator(object):
    """Provides methods for communication with blip.pl via API 0.02."""

    def __init__(self, userName = None, password = None, userAgent = None):
        """Initializes communicator object. You can provide userName and
        password to create authenticated communicator. You may also specify
        userAgent string to send to the blip server in every request."""

        self.limit = 50
        self.userName = userName
        self.password = password
        self.userAgent = userAgent

    def __GetConnection(self):
        """Returns fresh connection to Blip"""

        self.conn = httplib.HTTPConnection(BLIP_API_URL)
        return self.conn
#        return httplib.HTTPConnection(BLIP_API_URL)
        

    def closeConnection(self):
        """Closes connection to Blip (avoids timeout)"""

        return self.conn.close()
#        return True

    def __MakeHeaders(self, auth):
        """Makes http headers compatible with Blip API"""

        headers = dict()
        headers["X-Blip-api"] = BLIP_API_VERSION
        headers["Accept"] = JSON
        if (auth and self.userName != None and self.password != None):
            credentials = self.userName + ":" + self.password;
            headers["Authorization"] = "Basic "+base64.b64encode(credentials)
        if (self.userAgent != None):
            headers["User-Agent"] = self.userAgent

        return headers

    def __PostJson(self, url, data):
        """Posts JSON to the server and returns http response"""

        jsonBody = cjson.encode(data)
        conn = self.__GetConnection()
        headers = self.__MakeHeaders(True)
        headers["Content-Type"] = JSON
        headers["Content-Length"] = str(len(jsonBody))
        conn.request("POST", url, jsonBody, headers)
        response = conn.getresponse()
        self.__CheckResponse(response)
        return response

    def __PostFile(self, url, fileName, prefix):
        """Uploads given file to the blip server using POST request"""
        CRLF = '\r\n'

        f = open(fileName, "rb")
        content = f.read()
        boundary = "-------------------------------"+ \
            "".join([ random.choice('0123456789') for x in range(28) ])

        output = []
        output.append("--"+boundary)
        output.append('Content-Disposition: form-data; name="'+prefix+ \
            '"; filename="avatar.png"')
        output.append('Content-Type: '+mimetypes.guess_type(fileName)[0] \
            or 'application/octet-stream')
        output.append("")
        output.append(content)
        output.append("--"+boundary+"--")
        output.append("")

        encoded = CRLF.join(output)

        conn = self.__GetConnection()
        headers = self.__MakeHeaders(True)

        conn.putrequest("POST", url)
        for (k,v) in headers.iteritems():
            conn.putheader(k, v)

        conn.putheader("Content-Type", "multipart/form-data; boundary=" + \
            boundary)
        conn.putheader("Content-Length", str(len(encoded)))

        conn.endheaders()
        conn.send(encoded)
        response = conn.getresponse()
        self.__CheckResponse(response)

    def __PutJson(self, url, data):
        """Puts JSON on the server and returns http response"""

        jsonBody = cjson.encode(data)
        conn = self.__GetConnection()
        headers = self.__MakeHeaders(True)
        headers["Content-Type"] = JSON
        headers["Content-Length"] = str(len(jsonBody))
        conn.request("PUT", url, jsonBody, headers)
        response = conn.getresponse()
        self.__CheckResponse(response)
        return response.read()

    def __GetJson(self, url, auth, responseProcessor = None):
        """Requests server (by GET) data in JSON format.
        Returns decoded object."""

        conn = self.__GetConnection()
        conn.request("GET", url, "", self.__MakeHeaders(auth))
        response = conn.getresponse()
        if (responseProcessor != None):
            if (responseProcessor(response) == False):
                return None

        self.__CheckResponse(response)
        data = response.read()
        return cjson.decode(data)

    def __GetJsonOrNone(self, url, auth):
        """Requests server (by GET) data in JSON format.
        Returns decoded object or None in case of 404."""

        return self.__GetJson(url, auth, \
        (lambda response: not response.status == httplib.NOT_FOUND))

    def __Delete(self, url, id = None):
        """Sends DELETE command to the blip server to delete resource"""

        conn = self.__GetConnection()
        if (id != None):
            url += "/" + str(id)
        conn.request("DELETE", url, "", self.__MakeHeaders(True))
        response = conn.getresponse()
        self.__CheckResponse(response)

    def __BuildGetUrl(self, baseUrl, userName = "", limit = -1, since = -1, offset = -1):
        """Builds URL string for GET operations"""

        url = "/"
        if (userName == self.userName):
            if (since < 1):
                url += baseUrl
            else:
                url += baseUrl+"/"+str(since)+"/since"
        elif (userName == ""):
            if (since < 1):
                url += baseUrl+"/all"
            else:
                url += baseUrl+"/"+str(since)+"/all_since"
        else:
            if (since < 1):
                url += "users/"+userName+"/"+baseUrl
            else:
                url += "users/"+userName+"/"+baseUrl+"/"+str(since)+"/since"

        if (limit > 0 and offset == -1):
            url += "?limit="+str(limit)
        elif (offset > 0 and limit == -1):
            url += "?offset="+str(offset)
        elif (limit > 0 and offset > 0):
            url += "?limit="+str(limit)+"&offset="+str(offset)

        return url

    def __BuildGetUrlRev(self, baseUrl, userName = "", limit = -1, since = -1, offset = -1):
        """Builds URL string for GET operations"""

        url = "/"
        if (userName == self.userName):
            if (since < 1):
                url += baseUrl
            else:
                url += baseUrl+"/since"+"/"+str(since)
        elif (userName == ""):
            if (since < 1):
                url += baseUrl+"/all"
            else:
                url += baseUrl+"/"+str(since)+"/all_since"
        else:
            if (since < 1):
                url += "users/"+userName+"/"+baseUrl
            else:
                url += "users/"+userName+"/"+baseUrl+"/"+"since/" + str(since)

        if (limit > 0 and offset == -1):
            url += "?limit="+str(limit)
        elif (offset > 0 and limit == -1):
            url += "?offset="+str(offset)
        elif (limit > 0 and offset > 0):
            url += "?limit="+str(limit)+"&offset="+str(offset)

        return url

    def __CheckResponse(self, response):
        """Check whether response is correct (code 20x)"""

        status = response.status
        if (status == httplib.OK or status == httplib.CREATED
            or status == httplib.NO_CONTENT):
            return
        elif (status == httplib.UNAUTHORIZED):
            raise BadCredentialsException
        elif (status == httplib.SERVICE_UNAVAILABLE):
            raise ServerBusyException
        elif (status == httplib.BAD_REQUEST
            or status == httplib.UNPROCESSABLE_ENTITY):
            raise BadArgumentsException
        elif (status == httplib.NOT_FOUND):
            raise NotFoundException
        else:
            raise BadOperationException

# bliposphere

    def GetBliposphere(self, limit = -1, offset = -1):
        """Gets bliposphere updates"""

        if (limit < 1):
            limit = self.limit
        if (offset < 0):
            offset = 0

        return self.__GetJson("/bliposphere?limit="+str(limit)+"&offset="+str(offset), False)

# dashboard

    def GetDashboard(self, limit = -1, since = -1, offset = -1):
        """Gets recent updates from user's dashboard"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrlRev("dashboard", self.userName, limit, since, offset)
        return self.__GetJson(url, True)

    def GetDashboardForUser(self, userName, limit = -1, since = -1, offset = -1):
        """Gets recent updates from specified user's dashboard"""

        if (limit < 1):
            limit = self.limit
            
        if since > 0:
            limit = -1

        url = self.__BuildGetUrlRev("dashboard", userName, limit, since, offset)
        return self.__GetJson(url, True)
        
# updates (statuses + directed messages)

    def GetUpdates(self, limit = -1, since = -1, offset = -1):
        """Gets updates for current user"""
        
        if (limit < 1):
            limit = self.limit
            
        url = self.__BuildGetUrl("updates", self.userName, limit, since, offset)
        return self.__GetJson(url, True)

    def GetUpdatesForUser(self, userName, limit = -1, since = -1, offset = -1):
        """Gets updates for specified user"""
        
        if (limit < 1):
            limit = self.limit
            
        url = self.__BuildGetUrl("updates", userName, limit, since, offset)
        return self.__GetJson(url, True)
        
    def GetUpdatesForAll(self, limit = -1, since = -1, offset = -1):
        """Gets updates for all users"""
        
        if (limit < 1):
            limit = self.limit
            
        url = self.__BuildGetUrl("updates", "", limit, since, offset)
        return self.__GetJson(url, True)

    def SendUpdate(self, body):
        """Adds a new update by the user. Use UTF-8 string."""

        status = {"update" : {"body" : unicode(body, "utf-8")}}
        self.__PostJson("/updates", status)
        
# statuses

    def GetStatuses(self, limit = -1, since = -1, offset = -1):
        """Gets statuses for current user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("statuses", self.userName, limit, since, offset)
        return self.__GetJson(url, True)

    def GetStatusesForUser(self, userName, limit = -1, since = -1, offset = -1):
        """Gets statuses for specified user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("statuses", userName, limit, since, offset)
        return self.__GetJson(url, True)

    def GetStatusesForAll(self, limit = -1, since = -1, offset = -1):
        """Gets statuses for all users"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("statuses", "", limit, since, offset)
        return self.__GetJson(url, True)

    def SendStatus(self, body):
        """Adds a new status for the user. Use UTF-8 string."""

        status = {"status" : {"body" : unicode(body, "utf-8")}}
        self.__PostJson("/statuses", status)

    def DeleteStatus(self, id):
        """Removes status with given id from blip"""

        self.__Delete("/updates", id)

# (direct) messages

    def GetMessages(self, limit = -1, since = -1, offset = -1):
        """Gets directed messages of current user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("directed_messages", self.userName,
            limit, since, offset)
        return self.__GetJson(url, True)

    def GetMessagesForUser(self, userName, limit = -1, since = -1, offset = -1):
        """Gets messages directed to given user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("directed_messages", userName,
            limit, since, offset)
        return self.__GetJson(url, True)

    def GetMessagesForAll(self, limit = -1, since = -1, offset = -1):
        """Gets directed messages for all users"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("directed_messages", "",
            limit, since, offset)
        return self.__GetJson(url, True)

    def SendMessage(self, userName, body):
        """Adds a message directed to given user. Use UTF-8 string."""

        message = {"directed_message" : {
            "body" : unicode(body, "utf-8"),
            "recipient" : unicode(userName, "utf-8") }}
        self.__PostJson("/directed_messages", message)

    def DeleteMessage(self, id):
        """Removes directed message with given id"""

        self.__Delete("/directed_messages", id)

# update additions

    def GetMovie(self, id):
        """Retrieves info about movie related to the update with id"""

        return self.__GetJson("/updates/"+str(id)+"/movie", False)

    def GetRecording(self, id):
        """Retrieves info about recording related to the update with id"""

        return self.__GetJson("/updates/"+str(id)+"/recording", False)

    def GetPicture(self, id):
        """Retrives info about picture related to the update with id"""

        return self.__GetJson("/updates/"+str(id)+"/pictures", False)

    def GetPicturesForAll(self, limit = -1, since = -1):
        """Retrives info about pictures posted by any user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("pictures", "", limit, since)
        return self.__GetJson(url, False)

    def GetShortLinksForAll(self, limit = -1, since = -1):
        """Gets info about short links posted by any user"""

        if (limit < 1):
            limit = self.limit

        url = self.__BuildGetUrl("shortlinks", "", limit, since)
        return self.__GetJson(url, False)

# users

    def GetUser(self, userName):
        """Gets info about specified user"""

        return self.__GetJson("/users/"+userName, False)

# subscriptions

    def GetSubscriptions(self):
        """Returns all subscriptions for current user"""

        return self.__GetJson("/subscriptions", True)

    def GetSubscriptionsFrom(self):
        """Returns all observed users by current user"""

        return self.__GetJson("/subscriptions/from", True)

    def GetSubscriptionsTo(self):
        """Returns all users that observe current user"""

        return self.__GetJson("/subscriptions/to", True)

    def GetSubscriptionsForUser(self, userName):
        """Returns all subscriptions for given user"""

        return self.__GetJson("/users/"+userName+"/subscriptions", True)

    def GetSubscriptionsFromUser(self, userName):
        """Returns all observed users by given user"""

        return self.__GetJson("/users/"+userName+"/subscriptions/from", True)

    def GetSubscriptionsToUser(self, userName):
        """Returns all users that observe given user"""

        return self.__GetJson("/users/"+userName+"/subscriptions/to", True)

    def RemoveSubscription(self, observedUser):
        """Delete current user's subscription of given user"""

        self.__Delete("/subscriptions/"+observedUser)

    def MakeSubscription(self, observedUser, www = True, im = False):
        """Creates a subscription of given user's actions"""

        if (www == False and im == False):
            return

        data = { "subscription" : { "im" : im, "www" : www } }
        self.__PutJson("/subscriptions/"+observedUser, data)

# archives

    def GetArchive(self, userName = "", yr = 2007, mon = 0, offset = 0, limit = 0):
        """Gets avatar info for current user"""

        u = self.userName
        if (userName != ""):
            u = userName
        
        d = ""

        if (yr > 2007 and mon > 0):
            d = "/"+str(yr)+"/"+str(mon)

        url = "/users/"+u+"/archives"+d
        q = []
        
        if (offset > 0):
            q.append("offset="+str(offset))
        
        if (limit > 0):
            q.append("limit="+str(limit))

        if (len(q)):
            url += "?"+"&".join(q)

#        print url
        return self.__GetJson(url, False)

# avatar

    def GetAvatar(self):
        """Gets avatar info for current user"""

        return self.__GetJsonOrNone("/users/"+self.userName+"/avatar", False)

    def GetAvatarForUser(self, userName):
        """Gets avatar for given user"""

        return self.__GetJsonOrNone("/users/"+userName+"/avatar", False)

    def DeleteAvatar(self):
        """Removes avatar of current user"""

        return self.__Delete("/avatar")

    def SetAvatar(self, fileName):
        """Sets a new avatar for current user"""

        self.__PostFile("/avatar", fileName, "avatar[file]")

# background

    def GetBackground(self):
        """Gets background info for current user"""

        return self.__GetJsonOrNone("/users/"+self.userName+"/background", False)

    def GetBackgroundForUser(self, userName):
        """Gets background info for given user"""

        return self.__GetJsonOrNone("/users/"+userName+"/background", False,)

    def DeleteBackground(self):
        """Removes background for current user"""

        return self.__Delete("/background")

    def SetBackground(self, fileName):
        """Sets a new background for current user"""
        self.__PostFile("/background", fileName, "background[file]")

class CommandQueue(object):
    """Asynchronous command queue that can be used to communicate with blip.pl 
    in the background."""
    
    def __init__(self):
        self.queue = Queue()
        self.worker = threading.Thread(target=self.__worker)
        self.worker.setDaemon(True)
	
    def __del__(self):
        self.Finish()
        
    def __worker(self):
        while True:
            item = self.queue.get(True)
            item()
            self.queue.task_done()
	    
    def Finish(self):
        """Finishes all commands in the queue"""
	
        self.queue.join()
	
    def HasPendingCommands(self):
        """Returns True if the queue is busy"""
	
        return self.queue.qsize() > 0
	
    def Enqueue(self, command):
        """Enqueues a command in the queue. 
        Command must refer to a function without parameters."""

        self.queue.put(command)
        
class BlipManager(object):
    """Manages a blip session for given user or anonymously"""
    
    def __init__(self, userName, password):
        self.communicator = Communicator(userName, password)
        self.queue = CommandQueue()
        
    
