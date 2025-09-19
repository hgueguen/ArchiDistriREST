from flask import Flask, request, jsonify, make_response
import json
import requests
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'
USER_SERVICE_URL = "http://localhost:3203"

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

# Récupérer toutes les réservations ( doit être admin )
@app.route("/bookings", methods=['GET'])
def get_bookings():
   requester_id = request.args.get('requester_id')
   if not requester_id:
      return make_response(jsonify({"error":"requester_id is required"}),400)
   
   user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")

   if user_response.status_code != 200:
      return make_response(jsonify({"error":"Requester not found"}),404)
   user = user_response.json()
   is_admin = user.get("admin") == True
   if is_admin:
      res = make_response(jsonify(bookings), 200)
      return res
   else:
      return make_response(jsonify({"error":"Only admins can access this resource"}),403)
   
# Récupérer une réservation pour chaque utilisateur (doit etre admin ou le propriétaire de la réservation)
@app.route("/bookings/<userid>", methods=['GET'])
def get_booking_by_userid(userid):
   requester_id = request.args.get('requester_id')
   if not requester_id:
      return make_response(jsonify({"error":"requester_id is required"}),400)
   
   user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")

   if user_response.status_code != 200:
      return make_response(jsonify({"error":"Requester not found"}),404)
   user = user_response.json()
   is_admin = user.get("admin") == True
   is_owner = str(requester_id) == str(userid)
   if is_admin or is_owner:
      user_bookings = [b for b in bookings if str(b["userid"]) == str(userid)]
      res = make_response(jsonify(user_bookings), 200)
      return res
   else:
      return make_response(jsonify({"error":"Only admins or the owner can access this resource"}),403)


   
if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
