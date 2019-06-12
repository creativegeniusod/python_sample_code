# project/server/auth/booking.py

from flask import request, make_response, jsonify
from flask.views import MethodView

from project.server import app, bcrypt, db
from project.server.models import Booking, User
import datetime
from pytz import timezone
class BookingAPI(MethodView):
    """
    Booking Resource
    """
    
    def post(self):
        token_response = User.check_token_exists(request)
        http_code = token_response['code']

        if token_response['status'] == 'fail':
            token_response.pop('code', None)
            return make_response(jsonify(token_response)),http_code
        
        # get the post data
        post_data = request.get_json()
        worker_id, booking_date, booking_time, booking_type = post_data.get('worker_id'),post_data.get('date'), post_data.get('time'), post_data.get('type')
        valid_types = ["instant","later"]

        if booking_type not in valid_types:
            responseObject = {
                'status' : 'fail',
                'message': 'Invalid booking type.',
            }
            return make_response(jsonify(responseObject)), 400

        customer_id = token_response['data']['id']
        if worker_id == customer_id:
            responseObject = {
                'status' : 'fail',
                'message': 'Same user cannot book himself.',
            }
            return make_response(jsonify(responseObject)), 400
            
        #check whether any unbilled completed booking present (all booking amount must be paid before making any new booking)
        payment_record = Booking.booking_payment_status(customer_id)
        http_code = payment_record['code']

        if payment_record['status'] == 'fail':
            payment_record.pop('code', None)
            return make_response(jsonify(payment_record)),http_code
            

        worker_object = User.get_user_by_id(worker_id,'worker')
        
        # check if user is not worker
        if token_response['data']['role'] == worker_object.role:
            responseObject = {
                'status' : 'fail',
                'message': 'Same user type is not allowed to create booking. Be agent to create a booking.',
            }
            return make_response(jsonify(responseObject)), 400

        # if worker available
        if worker_object in [None,False]:
            responseObject = {
                'status' : 'fail',
                'message': 'Customer is not allowed to book another customer. Please pass valid id of a worker.',
            }
            return make_response(jsonify(responseObject)), 400

        #check if passed worker id matched with exisiting one in dB (double check)
        if (int)(worker_object.id) != (int)(worker_id):
            responseObject = {
                'status' : 'fail',
                'message': 'Worker info mismatch.',
            }
            return make_response(jsonify(responseObject)), 400    

        # check if booking already exists
        query_filter = Booking.query.filter_by(customer_id=customer_id).filter_by(booking_type=booking_type)

        #in case of instant, we will check whether booking exists for same worker[restrict multiple bookings for same worker] and same status or not
        if booking_type == "instant":
            query_filter = query_filter.filter_by(worker_id=worker_id).filter( (Booking.status == 'pending') | (Booking.status == 'accept') | (Booking.status == 'start') )

        #in case of later, we will check the booking exists for same date & time
        if booking_type == "later":
            laterTime = booking_date+""+booking_time
            formatted_date = datetime.datetime.strptime(laterTime, "%m%d%Y%H%M")
            query_filter = query_filter.filter_by(booking_time=formatted_date)
            
        booking = query_filter.first()
 
        if not booking:
            try:
                booking = Booking(
                    customer_id=customer_id,
                    worker_id=worker_object.id,
                    booking_type=booking_type,
                    status=post_data.get('status') if post_data.get('status') is not None else 'pending',
                    booking_date=booking_date,
                    booking_time=booking_time,
                    payment_status=False,
                    booking_price=worker_object.service_rate
                )
                # insert the booking record
                db.session.add(booking)
                db.session.commit()
                
                responseObject = {
                    'status' : 'success',
                    'message': 'Booking saved successfully!',
                    'data':{
                        'id': booking.id,
                        'booking_id': booking.booking_id
                    }
                }
                return make_response(jsonify(responseObject)), 201
            except Exception as e:
                responseObject = {
                    'status' : 'fail',
                    'message': 'Some error occurred while saving booking. Please try again.'
                }
                return make_response(jsonify(responseObject)), 401
        else:
            responseObject = {
                'status' : 'fail',
                'message': 'Booking already exists. Please ask worker to accept/complete it or you can cancel it on your own.',
            }
            return make_response(jsonify(responseObject)), 202

    '''function to retreive the list of workers as per booking_type & service_id'''
    def get(self,page,booking_type=None,service_id=0,latitude=None,longitude=None):
        # get the members list
        token_response = User.check_token_exists(request)
        http_code = token_response['code']
        valid_types = ["instant","later"]

        if token_response['status'] == 'fail':
            token_response.pop('code', None)
            return make_response(jsonify(token_response)),http_code
        
        '''
         service_id will be zero when we only need to fetch workers on behalf 
         of booking filters (instant/later)
        '''
        if service_id == 0:
            responseObject = {
                'status' : 'fail',
                'message': 'You need to select valid service.',
            }
            return make_response(jsonify(responseObject)), 400
        
        if booking_type is not None and booking_type not in valid_types:
            responseObject = {
                'status' : 'fail',
                'message': 'Invalid booking type.',
            }
            return make_response(jsonify(responseObject)), 400

        user_id = token_response['data']['id']
        user_role = token_response['data']['role']
        
        if user_role == 'worker' or user_role == 'admin'  :
            responseObject = {
                'status' : 'fail',
                'message': user_role+' is not allowed to access this endpoint.',
            }
            return make_response(jsonify(responseObject)), 400
        
        if user_id and user_role == 'customer':
            latitude  = latitude  if latitude  is not None else token_response['data']['latitude']
            longitude = longitude if longitude is not None else token_response['data']['longitude']

            workers = User.get_booking_members(page,booking_type,service_id,user_id,latitude,longitude)
            return make_response(jsonify(workers)), 200


    '''This method is to change the status of booking.'''
    def put(self,booking_id):
        token_response = User.check_token_exists(request)
        http_code = token_response['code']

        if token_response['status'] == 'fail':
            token_response.pop('code', None)
            return make_response(jsonify(token_response)),http_code
        
        user_id = token_response['data']['id']
        status = request.get_json().get('status')
        user_obj = User.get_user_by_id(user_id,'worker',True)
        
        # if worker is not found in dB
        if user_obj in [None,False] or not user_obj:
            responseObject = {
                'status' : 'fail',
                'message': 'Either user does not exists or not of worker type.',
            }
            return make_response(jsonify(responseObject)), 400
        
        #if stripe_account_id doesn't exists & logged user is worker
        if( (status == "accept") and (user_obj['stripe_account_id'] == None) and (user_obj['role'] == 'worker')):
            responseObject = {
                'status' : 'fail',
                'message': 'Account is not created on stripe. Please create account first on stripe.',
                'data':{'stripe':{'client_id':app.config.get('STRIPE_CLIENT_ID'),'scope':'read_write','redirect_uri':'/auth/payment/account'}}
            }
            return make_response(jsonify(responseObject)), 400

        booking_response = Booking.update_booking_status(booking_id,status);
        http_code = booking_response['code']
        
        booking_response.pop('code', None)

        if booking_response['status'] == 'fail':
            return make_response(jsonify(booking_response)),http_code
        
        return make_response(jsonify(booking_response)), http_code

class BookingRecordsAPI(MethodView):
    '''function to retreive the list of workers as per booking_type'''
    def get(self,record_type=None, page=None):
        page = page if not None else 1
        token_response = User.check_token_exists(request)
        http_code = token_response['code']

        if token_response['status'] == 'fail':
            token_response.pop('code', None)
            return make_response(jsonify(token_response)),http_code
        
        user_id = token_response['data']['id']
        if record_type is None:
            responseObject = {
                'status' : 'fail',
                'message': 'Please provide the type of records you need.',
            }
            return make_response(jsonify(responseObject)), 400
        
        user_role = token_response['data']['role']
        if user_role:
            booking_record = Booking.get_booking_records(user_id,user_role,page,record_type)
            return make_response(jsonify(booking_record)), 200

# define the API resources
booking_view = BookingAPI.as_view('booking_api')
booking_records_view = BookingRecordsAPI.as_view('booking_records_api')