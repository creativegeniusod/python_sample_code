import json
import random
import string

from django.shortcuts import render, redirect
from loginMongo.models import *
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from users.models import *
from chat.models import *
from virtualize.models import *
from datetime import datetime
from django.db import models
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http.response import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.utils.datastructures import MultiValueDictKeyError
import pytz
from .form import FileUploadForm
from django.core.mail import send_mail
from urllib.request import urlretrieve

def sendInviteEmail(request):
	if request.method == 'GET':
		toemail = request.GET['email'];
		
		res = send_mail("hello", "We are AI Assistant for Designers <br> Register for Adevi account <a href='http://localhost:7000/register/'>here</a>.", "tech2@edwayapps.com", [toemail], fail_silently=False)
		
		return HttpResponse('%s'%res)


#function to open chatbox
def getChatBox(request):
	if request.method == 'GET':
		chatWithUserId = request.GET['id'];
		if len(chatWithUserId) == 24:
			chatWithUserObj = []
			loggedUserObj = getUserObj(str(request.user));
			fromId = getUserSqliteId(str(request.user))[0];
			UserData = db.user.find({'_id': ObjectId(chatWithUserId)})
			for dt in UserData:
				chatWithUserObj.append({
					'id': str(dt['_id']),
					'username': dt['username'],
					'firstName': dt['firstName'],
					'lastName' : dt['lastName'],
					'email': dt['email'],
					'accountType': dt['accountType'],
					'profile': getUserPicture(dt['username'])})
			
			mongoId = getMongoId(request)
			
			allMessages = getAllMessages(chatWithUserId,mongoId);
			toImage = imgp = db['user'].find_one({'_id':ObjectId(chatWithUserId)})['profilePicture']
			fromImage = getUserPicture(str(request.user));

			for each_new in allMessages:
				objectId = each_new['_id']
				db.messages.update({'_id':ObjectId(objectId)}, {'$set': {'status': "1"}})

			return render(request, 'customize/includes/chatBoxView.html', {'from':loggedUserObj,'fromImage':fromImage,'to':chatWithUserObj,'toImage':toImage,'fromId':mongoId,'allMessages':allMessages,'type':'register'})
		else:
			jsonCurrentid = []
			jsonGuest = []
			jsonMessage = []
			currentuser = request.user.username
			cuser = getUserObj(currentuser)
			for cu in cuser:
				jsonCurrentid.append({'id': str(cu['_id'])})

			abcurrentid = jsonCurrentid[0]
			chatWithGuest = db.guestHiring.find({'guest_id': chatWithUserId})
			for cg in chatWithGuest:
				jsonGuest.append({'id': str(cg['_id']), 'email': cg['email'], 'firstName': cg['firstName'], 'lastName': cg['lastName'], 'user_type': cg['user_type'], 'owner_id': cg['owner_id'], 'project_id': cg['project_id'], 'guest_id': cg['guest_id'], 'hired_at': cg['hired_at']})
			
			allMessages = getAllMessagesguest(chatWithUserId,abcurrentid['id']);
			for am in allMessages:
				jsonMessage.append({'id': str(am['_id']), 'to': am['to'], 'message': am['message'], 'from_id': am['guest_id'], 'status': am['status'], 'created_at': am['created_at'], 'attached_files': am['attached_files'], 'file_type': am['file_type']})
			
			fromImage = getUserPicture(str(request.user));
			for each_new in allMessages:
				objectId = each_new['_id']
				db.messages.update({'_id':ObjectId(objectId)}, {'$set': {'status': "1"}})

			return render(request, 'customize/includes/chatBoxView.html', {'fromImage':fromImage,'to':jsonGuest,'fromId':abcurrentid['id'],'allMessages':jsonMessage,'type':'guest'})
	else:	
		return render(request, 'customize/includes/chatBoxView.html')


#function for save chat in DB
def saveChatMessage(request):
	if request.method == 'POST':
		toId = request.POST['to_id'].strip();
		if len(toId) == 24:
			jsontoid = []
			messageContent = request.POST['content'].strip();
			loggedUserObj = getUserObj(str(request.user));
			chatWithUserObj = getUserObjById(toId);
			fromId = getUserSqliteId(str(request.user))[0];
			mongoId = getMongoId(request)
			
			uploadedFilePath = uploadAttachments(request)
			fileExt = uploadedFilePath[-4:]
			#save message to mongodB
			chatsave(toId, messageContent, mongoId,uploadedFilePath,fileExt);

			allMessages = getAllMessages(toId,fromId);
			
			fromImage = getUserPicture(str(request.user));
			
			return render(request, 'customize/includes/fromMessage.html', {'from':loggedUserObj,'fromImage':fromImage,'message':messageContent,'uploaded_file_url':uploadedFilePath,'fileExt':fileExt,'type':'register'})
		else:
			jsonCurrentid = []
			messageContent = request.POST['content'].strip();
			currentuser = request.user.username
			fromImage = getUserPicture(str(currentuser));
			cuser = getUserObj(currentuser)
			for cu in cuser:
				jsonCurrentid.append({'id': str(cu['_id'])})

			abcurrentid = jsonCurrentid[0]
			uploadedFilePath = uploadAttachments(request)
			fileExt = uploadedFilePath[-4:]
			guestchatsave(toId, messageContent, abcurrentid['id'], uploadedFilePath, fileExt)

			allMessages = getAllMessagesguest(toId,abcurrentid['id']);

			return render(request, 'customize/includes/fromMessage.html', {'fromImage':fromImage, 'message':messageContent,'uploaded_file_url':uploadedFilePath,'fileExt':fileExt,'type':'guest'})

	else:	
		return render(request, 'customize/includes/chatBoxView.html', {'from':loggedUserObj,'fromImage':fromImage,'to':chatWithUserObj,'toImage':toImage,'fromId':fromId,'allMessages':allMessages})


#function for save chat in DB for Guest user
def guestsaveChatMessageG(request):
	if request.method == 'POST':
		toId = request.POST['to_id'].strip();
		fromId = request.POST['from_id'].strip();
		messageContent = request.POST['content'].strip();
		uploadedFilePath = uploadAttachments(request)
		fileExt = uploadedFilePath[-4:]
		#save message to mongodB
		if uploadedFilePath:
			img_toId = request.POST['forimage'].strip();
			guestchatsave(fromId, messageContent, img_toId, uploadedFilePath, fileExt)
		else:
			guestchatsave(toId, messageContent, fromId, uploadedFilePath, fileExt)

		return render(request, 'customize/includes/fromMessageGuest.html', {'message':messageContent,'uploaded_file_url':uploadedFilePath,'fileExt':fileExt})
	else:	
		return render(request, 'customize/includes/chatBoxViewGuest.html', {'from':loggedUserObj,'fromImage':fromImage,'to':chatWithUserObj,'toImage':toImage,'fromId':fromId,'allMessages':allMessages})

#function to open chatbox for Guest user
def guestgetChatBoxG(request):
	if request.method == 'GET':
		chatWithUserId = request.GET['id'];
		fromId = request.GET['guestid'];
				
		imgp = db['user'].find_one({'_id':ObjectId(chatWithUserId)})['profilePicture']
		allMessages = getAllMessagesguest(chatWithUserId,fromId);
		for each_new in allMessages:
			objectId = each_new['_id']
			db.guestMessages.update({'_id':ObjectId(objectId)}, {'$set': {'status': "1"}})
	
		return render(request, 'customize/includes/chatBoxViewGuest.html', {'fromImage':imgp, 'fromId':fromId,'allMessages':allMessages,'toowner':chatWithUserId})
	else:	
		return render(request, 'customize/includes/chatBoxViewGuest.html')

def uploadAttachments(request):
	if request.method == 'POST':
		uploaded_file_url = ""
		form = FileUploadForm(request.POST,request.FILES)
		if request.FILES.get('file_source', False):
			myfile = request.FILES['file_source']
			fs = FileSystemStorage()
			filename = fs.save(myfile.name, myfile)
			uploaded_file_url = fs.url(filename)
		
		return uploaded_file_url;
		

def getAllMessages(toId,fromId):
	all_message = []
	messages = db.messages.find({
		 	'$or': [{
		        'from_id': fromId,'to': toId
		  		},{
		        'from_id': toId,'to': fromId
		    	}]
		});
	for each_obj in messages:
		all_message.append(each_obj)

	return all_message;

# get all message for Guest user
def getAllMessagesguest(toId,fromId):
	all_messageg = []
	messages = db.guestMessages.find({
		 	'$or': [{
		        'guest_id': fromId,'to': toId
		  		},{
		        'guest_id': toId,'to': fromId
		    	}]
		});
	for each_obj in messages:
		all_messageg.append(each_obj)

	return all_messageg;


def getNewMessage(request):
	allNewMessages = []
	if request.method == 'GET':
		onlyforcheck = request.GET['id'];
		if len(onlyforcheck) == 2:
			fromId = int(request.GET['id']);
			fromUserObj = getUserObjById(request.GET['id']);
			fromImage = getUserPicture(str(fromUserObj[10]));
			toId = getUserSqliteId(str(request.user))[0];
			
			messages = db.messages.find({'from_id':fromId,'to':toId,'status':'0'});
		
			if messages.count():
				for each_new in messages:
					objectId = each_new['_id']
					db.messages.update({'_id':ObjectId(objectId)}, {'$set': {'status': "1"}})
					allNewMessages.append(each_new)

			return render(request, 'customize/includes/toMessage.html',{'allMessages':allNewMessages,'fromImage':fromImage,'fromName':fromUserObj[10]})
		else:
			fromId = request.GET['id'];
			jsonCurrentid = []
			currentuser = request.user.username
			fromImage = getUserPicture(currentuser);
			cuser = getUserObj(currentuser)
			for cu in cuser:
				jsonCurrentid.append({'id': str(cu['_id'])})

			abcurrentid = jsonCurrentid[0]
			messages = db.guestMessages.find({'guest_id':fromId,'to':abcurrentid['id'],'status':'0'});

			if messages.count():
				for each_new in messages:
					objectId = each_new['_id']
					db.guestMessages.update({'_id':ObjectId(objectId)}, {'$set': {'status': "1"}})
					allNewMessages.append(each_new)
			
			return render(request, 'customize/includes/toMessage.html',{'allMessages':allNewMessages, 'fromImage':fromImage})


def updateMessageStatus():
	return "success";

def getMongoId(request):
    jsonCurrentid = []
    currentuser = request.user.username
    fromImage = getUserPicture(currentuser);
    cuser = getUserObj(currentuser)
    for cu in cuser:
        jsonCurrentid.append({'id': str(cu['_id'])})

    abcurrentid = jsonCurrentid[0]

    return abcurrentid['id']


def getNewMessagesLive(request):
	alluserCount = []
	allmsgCount = []
	allguestmsgCount = []
	finalCount = []
	if request.method == 'GET':
		allmongousers = getMongoUserExceptCurrentUser(str(request.user));
		my_dict1 = my_dict2 = my_dict3 = {}
		queryset = get_current_users()
		totalonline = queryset.count()
		my_dict3['total'] = {"tot": str(totalonline)}
		onlineresults = queryset.values_list('username', 'id')
		dicresult = dict(onlineresults)
		my_dict1['online'] = dicresult
		mongoId = getMongoId(request)
		for each_id in allmongousers:
			msgCount = getMessageCount(each_id['id'],mongoId);
			alluserCount.append(each_id['id'])
			allmsgCount.append(msgCount)

		dictA = zip(alluserCount, allmsgCount)
		for e_dictA in dictA:
			finalCount.append(e_dictA)

		my_dict2['count'] = dict(finalCount)
		dictM = merge_three_dicts(my_dict1, my_dict2, my_dict3)
		allguest = db.guestHiring.find({})
		for allg in allguest:
			msgCountG = getGuestMessageCount(allg['guest_id'], mongoId)
			allguestmsgCount.append({allg['guest_id']: msgCountG})
			
		dictM.update({'countguest': allguestmsgCount})
				
		jsonvar1 = json.dumps(dictM)

		return JsonResponse(jsonvar1, safe=False)

# for guest message count
def guestNewMessagesLiveG(request):
	if request.method == 'GET':
		guestid = request.GET['guestid']
		ownerid = request.GET['ownerid']
		dictM = []
		msgCountG = getGuestMessageCount(ownerid, guestid)
		dictM = {'countguest': {ownerid: msgCountG}}
		jsonvar1 = json.dumps(dictM)
		return JsonResponse(jsonvar1, safe=False)

def getMongoIdfor(request):
    jsonCurrentid = []
    currentuser = request.user.username
    fromImage = getUserPicture(currentuser);
    cuser = getUserObj(currentuser)
    for cu in cuser:
        jsonCurrentid.append({'id': str(cu['_id'])})

    abcurrentid = jsonCurrentid[0]

    return abcurrentid['id']