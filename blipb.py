#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

# blipb.py - backup blip contents (including pictures)

# This script will:

#     a) backup blip.pl json archive using API to text files
#     b) generate a script to be used later to fetch all the  pictures
#     uploaded to blip.pl account(s)

# Just run this script and it will create *-updates.json.txt files and print
# a shell script which will wget all the image files.  Run it afterwards to
# fetch images.

# Requirements:
# 1. a modified version of blippy.py by Patryk Bajger. My mod adds handling of
#    API's archive call.  You can find it at orfika.net.  Source can be found
#    at http://blippy.sourceforge.net/.
# 2. Python module cjson, a very fast JSON encoder/decoder for Python,
#    available in variety of Linux distros; in Ubuntu it's "python-cjson"
#    package.  Project's homepage is at
#    http://cheeseshop.python.org/pypi/python-cjson

# Configuration:
# Very simple. See configuration options in CONFIGURATION SECTION below.

# Example of usage:
# $ ./blipb.py | tee run.sh ; bash run.sh

# NOTE: Based on blip.pl API version 0.02 to be found at http://blipapi.wikidot.com/

# Homepage: http://orfika.net/src/blip-backup-in-python/

# Copyright 2011 Rafał Frühling <rafamiga@gmail.com>

# LICENCE: GPL
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# you should have received a copy of the GNU General Public License
# along with this program (or with Nagios); if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA
#

import types
import blippy
from datetime import date
from time import gmtime, strftime
import os
import sys 
import urlparse
import random
import errno

############ CONFIGURATION SECTION ############

# backup these users
#### CHANGE THIS!!! ##### 
#### CHANGE THIS!!! #####  
#### CHANGE THIS!!! ##### 
backup_blip_users = [ "rafamiga", "bando" ]

# directories to store backup contents
blip_backup_dir = "./blip-backup"
pic_dir = blip_backup_dir + "/pics"
picfull_dir = blip_backup_dir + "/user_generated/update_pictures"
json_dir = blip_backup_dir

# API login (blip.pl user)
#### CHANGE THESE!!! #####
#### CHANGE THESE!!! ##### 
#### CHANGE THESE!!! ##### 
blip_bkp_user = "tvp"
blip_bkp_pass = "marne1234"

inmsg_pic_skel = "http://blip.pl/user_generated/update_pictures/%d_inmsg.jpg"
json_file_skel = blip_backup_dir + "/%s.blip.pl-%04d-%02d.json.txt"

blip_bkp_agent = "blipb.py/0.1.2"

DEBUG = False

############ DO NOT CHANGE BELOW THIS POINT ############

def smart_str(s, encoding='utf-8', errors='strict', from_encoding='utf-8'):
    if type(s) in (int, long, float, types.NoneType):
        return str(s)
    elif type(s) is str:
        if encoding != from_encoding:
          return s.decode(from_encoding, errors).encode(encoding, errors)
        else:
            return s

    elif type(s) is unicode:
        return s.encode(encoding, errors)
    elif hasattr(s, '__str__'):
        return smart_str(str(s), encoding, errors, from_encoding)
    elif hasattr(s, '__unicode__'):
        return smart_str(unicode(s), encoding, errors, from_encoding)
    else:
        return smart_str(str(s), encoding, errors, from_encoding)

def tstamp():
  return "["+strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())+"]"

class BlipMonArchive:
  def __init__(self,user = "", year = 0,month = 0):
    self.arch = {}
    self.picuids = []
    self.year = year
    self.month = month
    self.user = user
    self.pics = {} # {picture_id: orig_url}
    
    if self.month == 0:
      self.month = date.today().month

    if self.year == 0:
      self.year = date.today().year
        
    if DEBUG:
      sys.stderr.write("*** u='"+user+"' y="+str(self.year)+" m="+str(self.month)+'\n')

    self.comm = blippy.Communicator(blip_bkp_user,blip_bkp_pass,blip_bkp_agent)

  def fetchArchiveData(self):
    archoffset = 0
    archlimit = 50
  
    while True:
      a = self.comm.GetArchive(self.user,self.year,self.month,archoffset,archlimit)

      if len(a) == 0:
        break
      else:
        a.reverse()
  
      for m in a:
        id = m['id']
        self.arch[m['id']] = m
        if DEBUG:
          sys.stderr.write("id="+str(id)+" "+m['created_at']+" "+m['body_formatted'].encode('utf-8')+'\n')

        if m['pictures_attached'] == True:
          self.picuids.append(id)

      if len(a) == archlimit:
        archoffset += archlimit
      else:
        break

    # list
    return self.arch

# {'update_path': '/updates/213366231', 'url': 'http://blip.pl/user_generated/update_pictures/1448497.jpg', 'id': 1448497}

# inmsg = http://blip.pl/user_generated/update_pictures/${id}_inmsg.jpg

  def fetchImageData(self):
    for id in self.picuids:
#      print "p id="+str(id),
      p = self.comm.GetPicture(id)[0]
      
      if DEBUG:
        sys.stderr.write("picid="+str(p['id'])+" url="+p['url']+'\n')
      self.pics[p['id']] = p['url'];

    # dictionary - key:id value:url
    return self.pics

  def closeConnection(self):
    self.comm.closeConnection()

#############

if len(blip_bkp_user) < 3 or len(blip_bkp_pass) < 6:
  raise AssertionError("blip.pl API user and/or password not set ** READ THE SCRIPT, LUKE... **")
  
print "# " + tstamp() + " " + blip_bkp_agent + "start ("+str(len(backup_blip_users))+" blip user(s))"
print "set -x"
print "echo '" + blip_bkp_agent + "'"

for user in backup_blip_users:
  yn = date.today().year
  mn = date.today().month

  if not os.path.exists(blip_backup_dir):
    print 'mkdir -p "'+blip_backup_dir+'"'

  if not os.path.exists(pic_dir):
    print 'mkdir -p "'+pic_dir+'"'

  if not os.path.exists(picfull_dir):
    print 'mkdir -p "'+picfull_dir+'"'

  print "# " + tstamp() + " user=" + user

  try:
    os.makedirs(json_dir)
  except OSError as exc:
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise
                                              
  ys = range(2007,yn-1)
  #ys = [ 2011 ]

  random.shuffle(ys)
  ys.insert(0,2010)

  for y in ys:

    ms = range(1,12)
    if y == 2007:
      ms = range(7,12)

  #  ms = [ 5 ]

    random.shuffle(ms)

    for m in ms:
      print "# " + tstamp() + " blip#("+str(y)+"," + "%02d" % m + ")=",
      b = BlipMonArchive(user,y,m)
      msgs = b.fetchArchiveData()
      msgsc = len(msgs)

      print str(msgsc),

      fn = json_file_skel % (user,y,m)
      print " fn="+fn,
      
      if len(msgs) > 0:
      
        try:
          f = open(fn, 'w')
          try:
            f.write(str(msgs))
          finally:
            f.close()

        except IOError as (errno, strerror):
          print "I/O error({0}): {1}".format(errno, strerror),

        except:
          print "Unexpected error: ", sys.exc_info()[0]
          raise

        pics = b.fetchImageData()
        picsc = len(pics)

        print " pics#=" + str(picsc)

        b.closeConnection()

        print "echo '" + user + " " + str(y) + "/" + "%02d" % m + "' #" + str(picsc) + " pic(s)'"

        print "# " + tstamp() + " wget " + str(picsc) + " pic(s)"

        for id,url in pics.iteritems():
#          print 'wget -q -P "'+pic_dir+'/'+str(id)+'_inmsg.jpg" '''+inmsg_pic_skel%id+"'"
          print 'wget -q -nd -N -P "'+pic_dir+'"' + " '"+inmsg_pic_skel%id+"'"
          picfile = os.path.basename(urlparse.urlparse(url)[2])
          print 'wget -q -nd -N -P "'+picfull_dir+'"'+" '"+url+"'"

      else:
        print " no msgs"

print "# " + tstamp() + " meta"
print "echo 'meta " + blip_bkp_agent + "'"
