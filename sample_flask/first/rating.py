# project/server/auth/rating.py

from flask import request, make_response, jsonify
from flask.views import MethodView

from project.server import bcrypt, db
from project.server.models import Rating, Booking, User

class RatingAPI(MethodView):
    """
    Booking Rating Resource
    """
    def post(self):
        token_response = User.check_token_exists(request)
        http_code = token_response['code']

        if token_response['status'] == 'fail':
            token_response.pop('code', None)
            return make_response(jsonify(token_response)),http_code
        
        user_role = token_response['data']['role']
        
        if user_role == "customer":
            # get the post data
            post_data = request.get_json()
            booking_id, worker_id, rating_value = post_data.get('booking_id'), post_data.get('worker_id'), post_data.get('ratings')
            customer_id = token_response['data']['id']
            
            if worker_id == customer_id:
                responseObject = {
                    'status': 'fail',
                    'message': 'You cannot rate yourself.',
                }
                return make_response(jsonify(responseObject)), 404
                 
            if (rating_value not in range(1,6)) or (not isinstance(rating_value, int)):
                responseObject = {
                    'status': 'fail',
                    'message': 'Rating value must lie in between 1-5 & must be integer.',
                }
                return make_response(jsonify(responseObject)), 404

            # check booking object exists or not
            booking_obj = Booking.get_booking_info(booking_id,customer_id,worker_id)
            if not booking_obj:
                responseObject = {
                    'status': 'fail',
                    'message': 'Booking for id '+str(booking_id)+' either not completed or not found .',
                }
                return make_response(jsonify(responseObject)), 404
                
            # check if rating of particular booking already provided or not
            rating = Rating.query.filter_by(booking_id=booking_id).filter_by(worker_id=worker_id).filter_by(customer_id=customer_id).first()

            if not rating:
                try:
                    rating = Rating(
                        booking_id=booking_id,
                        customer_id=customer_id,
                        worker_id=worker_id,
                        rating=rating_value
                    )
                    # insert the rating record
                    db.session.add(rating)
                    db.session.commit()
                    
                    responseObject = {
                        'status': 'success',
                        'message': 'Booking rating saved successfully!',
                        'id': rating.id,
                        'rating': rating.rating
                    }
                    return make_response(jsonify(responseObject)), 201
                except Exception as e:
                    responseObject = {
                        'status': 'fail',
                        'message': 'Some error occurred. Please try again.'
                    }
                    return make_response(jsonify(responseObject)), 401
            else:
                responseObject = {
                    'status': 'fail',
                    'message': 'Rating already provided.',
                }
                return make_response(jsonify(responseObject)), 202
        else:
            responseObject = {
                    'status': 'fail',
                    'message': 'Worker cannot add rating to himself.',
            }
            return make_response(jsonify(responseObject)), 403

# define the API resources
rating_view = RatingAPI.as_view('rating_api')