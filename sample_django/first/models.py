import pytz
import sqlite3
from mongoengine import *
from django.db import models
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

#sqlite client 
conn_sqlite = sqlite3.connect('UserSessions.sqlite',check_same_thread=False)
cursor_sqlite = conn_sqlite.cursor()

client = MongoClient('localhost', 27017)
db = client.MeduzaDb

def getMongoIdbyusername(usernm):
    return db.user.find_one({'username': usernm},{'_id': 1})

def chatsave(to_id, message, from_id,attached_files=[],file_ext=""):
    db.messages.insert({
        'to': str(to_id),
        'message': message,
        'created_at': datetime.now(),
        'status': '0',
        'from_id': from_id,
        'attached_files': attached_files,
        'file_type': file_ext
    })

def guestchatsave(toId, message, from_id, attached_files=[], file_ext=""):
    db.guestMessages.insert({
        'to': toId,
        'message': message,
        'guest_id': from_id,
        'status': '0',
        'created_at': datetime.now(),
        'attached_files': attached_files,
        'file_type': file_ext
    })

def getMessageCount(fromId,toId):
	return db.messages.find({'from_id':fromId,'to':toId,'status':'0'}).count();

def getGuestMessageCount(fromId,toId):
    return db.guestMessages.find({'guest_id':fromId,'to':toId,'status':'0'}).count();

def merge_three_dicts(x, y, z):
    th = x.copy()
    th.update(y)
    newth = th.copy()
    newth.update(z)
    return newth

def Removedup(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    return final_list

# get mix record from "Hiring Details" table for chating purpose Param: userId (login user id)
def getChatUserFromHiringTable(userId):
    temp1 = []
    temp2 = []
    newhire = db.hiringDetails.find({
            '$or': [{
                'hireduserid': userId, 'accept_status': 'accepted'
                },{
                'hiredByid': userId, 'accept_status': 'accepted'
                }]
        });
    for jn in newhire:
        temp1.append({'hiredBy': jn['hiredBy']}) 
        temp2.append({'hiredusername': jn['hiredusername']})
    
    bothtemp = temp1 + temp2

    return Removedup(bothtemp)
