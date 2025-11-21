from flask import Flask, request, jsonify, make_response
import json
import requests
from werkzeug.exceptions import NotFound
from pymongo import MongoClient
import os

app = Flask(__name__)

PORT = 3001
HOST = '0.0.0.0'
USER_SERVICE_URL = "http://localhost:3203"
SCHEDULE_SERVICE_URL = "http://localhost:50051"
USEMONGO = os.getenv("USE_MONGO", "false").lower() == "true"
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017/archiDistriDB")

if USEMONGO:
   USER_SERVICE_URL = "http://user:3203"
   SCHEDULE_SERVICE_URL = "http://schedule:50051"
   client = MongoClient(MONGO_URL)
   db = client["archiDistriDB"]
   booking_collection = db["bookings"]
   if booking_collection.count_documents({}) == 0:
      with open('{}/data/bookings.json'.format("."), "r") as jsf:
         initial_bookings = json.load(jsf)["bookings"]
         booking_collection.insert_many(initial_bookings)
   bookings = list(booking_collection.find({}))
   for item in bookings:
      item["_id"] = str(item["_id"])
   
else:
   with open('{}/data/bookings.json'.format("."), "r") as jsf:
      bookings = json.load(jsf)["bookings"]

def write(bookings):
   with open('{}/data/bookings.json'.format("."), 'w') as f:
      full = {}
      full['bookings']=bookings
      json.dump(full, f)

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

# Récupérer toutes les réservations ( doit être admin )
@app.route("/bookings", methods=['GET'])
def get_bookings():
   if USEMONGO:
      bookings = list(booking_collection.find({}))
      for item in bookings:
         item["_id"] = str(item["_id"])
   

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
   if USEMONGO:
      bookings = list(booking_collection.find({}))
      for item in bookings:
         item["_id"] = str(item["_id"])

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

# Ajouter une réservation ( doit être admin ou le propriétaire de la réservation et le schedule doit exister )
@app.route("/bookings", methods=['POST'])
def add_booking():
    req = request.get_json()
    userid = req.get("userid")
    schedule_date = req.get("schedule_date")
    movieid = req.get("movieid")
    requester_id = req.get("requester_id")

    if not userid or not schedule_date or not movieid or not requester_id:
        return make_response(jsonify({"error": "userid, schedule_date, movieid and requester_id are required"}), 400)

    user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")
    if user_response.status_code != 200:
        return make_response(jsonify({"error": "Requester not found"}), 404)

    user = user_response.json()
    is_admin = user.get("admin") is True
    is_owner = str(requester_id) == str(userid)
    if not (is_admin or is_owner):
        return make_response(jsonify({"error": "Only admins or the owner can add a booking"}), 403)

    schedule_response = requests.get(f"{SCHEDULE_SERVICE_URL}/schedule/{schedule_date}")
    if schedule_response.status_code != 200:
        return make_response(jsonify({"error": "Schedule date not found"}), 404)

    schedule_data = schedule_response.json()
    movie_ids = schedule_data.get("movies", [])
    if str(movieid) not in [str(m) for m in movie_ids]:
        return make_response(jsonify({"error": "Movie ID not found in the schedule for the given date"}), 404)

    if USEMONGO:
        booking_collection = db["bookings"]
        booking = booking_collection.find_one({"userid": userid})
        if not booking:
            new_booking = {"userid": userid, "dates": [{"date": schedule_date, "movies": [movieid]}]}
            booking_collection.insert_one(new_booking)
            inserted = booking_collection.find_one({"userid": userid})
            inserted["_id"] = str(inserted["_id"])
            return make_response(jsonify(inserted), 200)
        else:
            dates = booking.get("dates", [])
            date_entry = next((d for d in dates if d["date"] == schedule_date), None)
            if not date_entry:
                new_date_entry = {"date": schedule_date, "movies": [movieid]}
                dates.append(new_date_entry)
            else:
                if movieid not in date_entry["movies"]:
                    date_entry["movies"].append(movieid)
                else:
                    return make_response(jsonify({"error": "Booking already exists"}), 400)
            booking_collection.update_one({"userid": userid}, {"$set": {"dates": dates}})
            updated = booking_collection.find_one({"userid": userid})
            updated["_id"] = str(updated["_id"])
            return make_response(jsonify(updated), 200)
    else:
        with open("./data/bookings.json", "r") as f:
            bookings_data = json.load(f)["bookings"]

        booking = next((b for b in bookings_data if str(b["userid"]) == str(userid)), None)
        if not booking:
            new_booking = {"userid": userid, "dates": [{"date": schedule_date, "movies": [movieid]}]}
            bookings_data.append(new_booking)
            with open("./data/bookings.json", "w") as f:
                json.dump({"bookings": bookings_data}, f)
            return make_response(jsonify(new_booking), 200)
        else:
            dates = booking.get("dates", [])
            date_entry = next((d for d in dates if d["date"] == schedule_date), None)
            if not date_entry:
                new_date_entry = {"date": schedule_date, "movies": [movieid]}
                dates.append(new_date_entry)
            else:
                if movieid not in date_entry["movies"]:
                    date_entry["movies"].append(movieid)
                else:
                    return make_response(jsonify({"error": "Booking already exists"}), 400)
            booking["dates"] = dates
            with open("./data/bookings.json", "w") as f:
                json.dump({"bookings": bookings_data}, f)
            return make_response(jsonify(date_entry if date_entry else new_date_entry), 200)

      

@app.route("/bookings/<userid>/<schedule_date>/<movieid>", methods=['DELETE'])
def delete_booking(userid, schedule_date, movieid):
    requester_id = request.args.get('requester_id')
    if not requester_id:
        return make_response(jsonify({"error": "requester_id is required"}), 400)

    user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")
    if user_response.status_code != 200:
        return make_response(jsonify({"error": "Requester not found"}), 404)

    user = user_response.json()
    is_admin = user.get("admin") is True
    is_owner = str(requester_id) == str(userid)
    if not (is_admin or is_owner):
        return make_response(jsonify({"error": "Only admins or the owner can delete a booking"}), 403)

    if USEMONGO:
        booking_collection = db["bookings"]
        booking = booking_collection.find_one({"userid": userid})
        if not booking:
            return make_response(jsonify({"error": "Booking not found for this user"}), 404)

        date_entry = next((d for d in booking.get("dates", []) if d["date"] == schedule_date), None)
        if not date_entry:
            return make_response(jsonify({"error": "Schedule date not found in user bookings"}), 404)

        if str(movieid) not in [str(m) for m in date_entry["movies"]]:
            return make_response(jsonify({"error": "Movie ID not found in the booking for the given date"}), 404)

        date_entry["movies"].remove(movieid)
        if not date_entry["movies"]:
            booking["dates"].remove(date_entry)
        if not booking["dates"]:
            booking_collection.delete_one({"userid": userid})
            return make_response(jsonify({"message": "Booking deleted successfully"}), 200)
        else:
            booking_collection.update_one({"userid": userid}, {"$set": {"dates": booking["dates"]}})
            return make_response(jsonify({"message": "Booking deleted successfully"}), 200)
    else:
        with open("./data/bookings.json", "r") as f:
            bookings_data = json.load(f)["bookings"]

        booking = next((b for b in bookings_data if str(b["userid"]) == str(userid)), None)
        if not booking:
            return make_response(jsonify({"error": "Booking not found for this user"}), 404)

        date_entry = next((d for d in booking.get("dates", []) if d["date"] == schedule_date), None)
        if not date_entry:
            return make_response(jsonify({"error": "Schedule date not found in user bookings"}), 404)

        if str(movieid) not in [str(m) for m in date_entry["movies"]]:
            return make_response(jsonify({"error": "Movie ID not found in the booking for the given date"}), 404)

        date_entry["movies"].remove(movieid)
        if not date_entry["movies"]:
            booking["dates"].remove(date_entry)
        if not booking["dates"]:
            bookings_data.remove(booking)

        with open("./data/bookings.json", "w") as f:
            json.dump({"bookings": bookings_data}, f)

        return make_response(jsonify({"message": "Booking deleted successfully"}), 200)


if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
