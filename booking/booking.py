from flask import Flask, request, jsonify, make_response
import json
import requests
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'
USER_SERVICE_URL = "http://localhost:3203"
SCHEDULE_SERVICE_URL = "http://localhost:3202"

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]

def write(bookings):
   with open('{}/databases/bookings.json'.format("."), 'w') as f:
      full = {}
      full['bookings']=bookings
      json.dump(full, f)

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

# Ajouter une réservation ( doit être admin ou le propriétaire de la réservation et le schedule doit exister )
@app.route("/bookings", methods=['POST'])
def add_booking():
   req = request.get_json()
   userid = req.get("userid")
   schedule_date = req.get("schedule_date")
   movieid = req.get("movieid")
   requester_id = req.get("requester_id")

   # Verification des champs requis
   if not userid or not schedule_date or not movieid or not requester_id:
      return make_response(jsonify({"error":"userid, schedule_date, movieid and requester_id are required"}),400)
   
   # Récupération des infos du requester
   user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")

   # Si celui effectuant la requête n'existe pas
   if user_response.status_code != 200:
      return make_response(jsonify({"error":"Requester not found"}),404)
   
   # Vérification si le requester est admin ou le propriétaire de la réservation
   user = user_response.json()
   is_admin = user.get("admin") == True
   is_owner = str(requester_id) == str(userid)
   if not (is_admin or is_owner):
      return make_response(jsonify({"error":"Only admins or the owner can add a booking"}),403)

   # Verification que la date du schedule existe
   schedule_response = requests.get(f"{SCHEDULE_SERVICE_URL}/schedule/{schedule_date}")
   if schedule_response.status_code != 200:
      return make_response(jsonify({"error":"Schedule date not found"}),404)
   schedule_data = schedule_response.json()
   # Verification que le movieid existe dans le schedule de la date donnée
   movie_ids = [m for m in schedule_data.get("movies", [])]
   if str(movieid) not in [str(m) for m in movie_ids]:
      return make_response(jsonify({"error":"Movie ID not found in the schedule for the given date"}),404)

   # S'il n'y a pas de réservation pour cet utilisateur, on en crée une nouvelle
   booking = next((b for b in bookings if str(b["userid"]) == str(userid)), None)
   if not booking:
      new_booking = {
         "userid": userid,
         "dates": [
            {
               "date": schedule_date,
               "movies": [movieid]
            }
         ]
      }
      bookings.append(new_booking)
      write(bookings)
      res = make_response(jsonify(new_booking),200)
      return res
   # S'il y a déjà une réservation pour cet utilisateur, on ajoute la date et le movieid
   else:
      date_entry = next((d for d in booking["dates"] if d["date"] == schedule_date), None)
      if not date_entry:
         new_date_entry = {
            "date": schedule_date,
            "movies": [movieid]
         }
         booking["dates"].append(new_date_entry)
         write(bookings)
         res = make_response(jsonify(new_date_entry),200)
         return res
      else:
         # La date existe déjà, on ajoute le movieid si ce n'est pas déjà fait
         if movieid not in date_entry["movies"]:
            date_entry["movies"].append(movieid)
            write(bookings)
            res = make_response(jsonify(date_entry),200)
            return res
         else:
            return make_response(jsonify({"error":"Booking already exists"}),400)
         

# suppréssion
@app.route("/bookings/<userid>/<schedule_date>/<movieid>", methods=['DELETE'])
def delete_booking(userid, schedule_date, movieid):
    requester_id = request.args.get('requester_id')
    if not requester_id:
        return make_response(jsonify({"error": "requester_id is required"}), 400)

    # Récupération des infos du requester
    user_response = requests.get(f"{USER_SERVICE_URL}/users/{requester_id}")
    if user_response.status_code != 200:
        return make_response(jsonify({"error": "Requester not found"}), 404)

    user = user_response.json()
    is_admin = user.get("admin") == True
    is_owner = str(requester_id) == str(userid)

    if not (is_admin or is_owner):
        return make_response(jsonify({"error": "Only admins or the owner can delete a booking"}), 403)

    # Recherche de la réservation de l'utilisateur
    booking = next((b for b in bookings if str(b["userid"]) == str(userid)), None)
    if not booking:
        return make_response(jsonify({"error": "Booking not found for this user"}), 404)

    # Recherche de la date dans les réservations de l'utilisateur
    date_entry = next((d for d in booking["dates"] if d["date"] == schedule_date), None)
    if not date_entry:
        return make_response(jsonify({"error": "Schedule date not found in user bookings"}), 404)

    # Recherche du movieid dans la liste des films pour cette date
    if str(movieid) not in [str(m) for m in date_entry["movies"]]:
        return make_response(jsonify({"error": "Movie ID not found in the booking for the given date"}), 404)

    # Suppression du movieid de la liste
    date_entry["movies"].remove(movieid)

    # Si la liste des films pour cette date est vide, on supprime la date
    if not date_entry["movies"]:
        booking["dates"].remove(date_entry)

    # Si la liste des dates est vide, on supprime la réservation de l'utilisateur
    if not booking["dates"]:
        bookings.remove(booking)

    write(bookings)
    return make_response(jsonify({"message": "Booking deleted successfully"}), 200)
   
   
if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
