# project/server/helpers.py

import string
import random
from twilio.rest import Client
from project.server import app, mail
from math import ceil, acos, cos, radians, sin, floor
from datetime import timedelta
from flask_mail import Message
import logging
import os.path as op
from werkzeug.utils import secure_filename
#from pyfcm import FCMNotification
from exponent_server_sdk import DeviceNotRegisteredError, PushClient, PushMessage, PushResponseError, PushServerError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
import jwt
import datetime
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
global timezone
timezone = pytz.timezone(app.config.get('TIMEZONE'))

# handle response to be send
def response_handler(response_status=False,response_message=False,response_data={},response_code=False):
	responseObject = {
		'status': response_status if response_status else 'fail',
		'message': response_message if response_message else 'Some error occurred during the process.',
		'data':response_data if response_data else {},
		'code':response_code if response_code else 401
	}
	return responseObject

# generate random string
def random_generator(size=8, type="mixed"):
	chars = string.ascii_lowercase + string.digits
	if type != "mixed":
		chars = string.digits
	return ''.join(random.choice(chars) for x in range(size))

# connect with twilio
def twilio_connect():
	account_sid = app.config.get('TWILIO_SID')
	auth_token = app.config.get('TWILIO_TOKEN')
	try:
		return Client(account_sid, auth_token)
	except Exception as e:
		logger.info( "Exception occurred in twilio connection :" + str(e) )
		raise e

# twilio message content
def twilio_message(otp_code):
	return "OTP-"+str(otp_code)+" .Please use this OTP to login in Application App. This OTP is valid for next "+str(app.config.get('OTP_EXPIRATION_TIME'))+" minutes."

# send message to user
def send_message(otp_code,send_to):
	response = {'status':'fail','data':False}
	if otp_code and send_to:
		client = twilio_connect()
				
		# prepare message body
		try:
			message_body = twilio_message(otp_code)
			message = client.messages.create(
				from_=app.config.get('TWILIO_FROM'),
				body=message_body,
				to=app.config.get('TWILIO_COUNTRY_CODE')+str(send_to))
			response = {'status':'success','data':True}
			pass
		except Exception as e:
			logger.info( "Exception occurred in sending message via twilio :" + str(e) )
			raise e

	return response


def calculate_radius(customer_latitude,customer_longitude,worker_latitude,worker_longitude, ceiled=False):
	distance = ( 6371 * acos(cos(radians(customer_latitude))*cos(radians(worker_latitude))*cos(radians(worker_longitude)-radians(customer_longitude))+sin(radians(customer_latitude))*sin(radians(worker_latitude))) )
	return distance if not ceiled else ceil(distance)

def booking_share(amount):
	worker_share = round(((amount*80)/100),2)
	application_share = round((amount-worker_share),2)
	return {'worker':worker_share,'application_share':application_share}

def calculate_booking_duration(start_time, end_time, booking_price):

	booking_response_obj = {'duration':0}
	difference = (end_time - start_time) 
	days, seconds = difference.days, difference.seconds
	hours, minutes = (((days * 24) + seconds)//3600), ((seconds % 3600)//60)

	#check for grace period [5 mins]
	if minutes > app.config.get('GRACE_PERIOD'): 
		'''if minutes greater than 5'''
		hours = hours + 1

	#the amount (service rate), when booking is made
	bookedPrice = booking_price if booking_price else app.config.get('BOOKING_PRICE')
	#calculate amount/hour
	basic_amount = hours * int(bookedPrice)

	#add stripe fixed rate (.30 cents)
	total_amount = basic_amount + app.config.get('STRIPE_FIXED_RATE')
	
	#add stripe transaction rate ($2.9 of amount)
	total_amount = round((total_amount/(1-(app.config.get('STRIPE_TRANSACTION_RATE')/100))),2)

	#calculate fee
	fees_amount = round((total_amount - basic_amount),2)

	booking_response_obj = {
		'duration':hours,
		'charge':{
			'basic':basic_amount,
			'total':total_amount,
			'fees':fees_amount
			},
		'share':booking_share(basic_amount)
	}
	return booking_response_obj

def send_push_notify(push_app_token, message={}):
	try:
		message_title = "Application Notification"
		message_body = "Hi, you have recevied new notification from Application."
	
		if message:
			message_title = message['title'] if message['title'] else message_title
			message_body = message['body'] if message['body'] else message_body
		
		#send push notification message to user device
		send_push_message(push_app_token, message_title, message_body);
		return True
		pass
	except Exception as e:
		logger.info( "Exception occurred in FCM (push notification) :" + str(e) )
		raise e

#function to send email to admin
def send_mail(subject=None,html=None, recipient=app.config.get('PASSWORD_RESET_EMAIL')):
	subject = subject if subject else "Login password updated"
	subject = "Application Admin Alert: "+subject
	html = html if html else "<p>There is some actions performed on Application admin panel.</p>"
	msg = Message(subject,
                  sender="security@application.com",
                  recipients=[recipient])
	msg.html = html
	mail.send(msg)

#function to generate thumbnail of uploaded image file
def thumb_name(filename):
    name, _ = op.splitext(filename)
    return secure_filename('%s-thumb.jpg' % name)

#function to generate prefix name of uploaded image file
def prefix_name(obj, file_data):
    parts = op.splitext(file_data.filename)
    return secure_filename(random_generator(3)+'-%s%s' % parts)


#function to verify whether the profile image path is valid or not 
def validate_image_name(image_url):
	if image_url:
		return image_url if "https" in image_url or "http" in image_url else image_url
	else:
		return ""

#function to get the absolute image path of an image from server
def get_absolute_url(image_name, user_id, type="profile"):
	if image_name:
		if type == "profile":
			return '/' + app.config.get('STATIC_IMAGE_DIR') + app.config.get('IMAGES_DIR') + app.config.get('PROFILE_FOLDER') + str(user_id) + "/" + image_name;
		else:
			return '/' + app.config.get('STATIC_IMAGE_DIR') + app.config.get('IMAGES_DIR') + app.config.get('PORTFOLIO_FOLDER') + str(user_id) + "/" + image_name;
	else:
		return ''


def send_push_message(token, title, message, extra=None):
    try:
        response = PushClient().publish(
            PushMessage(to=token,
            			title=title,
                        body=message,
                        data=extra))
    except PushServerError as exc:
        # Encountered some likely formatting/validation error.
        rollbar.report_exc_info(
            extra_data={
                'token': token,
                'message': message,
                'extra': extra,
                'errors': exc.errors,
                'response_data': exc.response_data,
            })
        raise
    except (ConnectionError, HTTPError) as exc:
        # Encountered some Connection or HTTP error - retry a few times in
        # case it is transient.
        rollbar.report_exc_info(
            extra_data={'token': token, 'message': message, 'extra': extra})
        raise self.retry(exc=exc)

    try:
        # We got a response back, but we don't know whether it's an error yet.
        # This call raises errors so we can handle them with normal exception
        # flows.
        response.validate_response()
    except DeviceNotRegisteredError:
        # Mark the push token as inactive
        
    except PushResponseError as exc:
        # Encountered some other per-notification error.
        rollbar.report_exc_info(
            extra_data={
                'token': token,
                'message': message,
                'extra': extra,
                'push_response': exc.push_response._asdict(),
            })        
        raise self.retry(exc=exc)

def generateToken(id):
	try:
	    payload = {
	        'exp': datetime.datetime.now(tz=timezone) + datetime.timedelta(days=app.config.get('TOKEN_EXP_DAYS'), hours=app.config.get('TOKEN_EXP_HOURS'), seconds=app.config.get('TOKEN_EXP_SECONDS')),
	        'iat': datetime.datetime.now(tz=timezone),
	        'sub': id,
	        'random_salt': random_generator(6,'mixed')
	    }
	    return jwt.encode(
	        payload,
	        app.config.get('SECRET_KEY'),
	        algorithm='HS256'
	    )
	except Exception as e:
	    logger.info( "Exception In Auth Token Encode :" + str(e) )
	    return e