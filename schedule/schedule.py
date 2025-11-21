import os
from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound
from pymongo import MongoClient

app = Flask(__name__)

PORT = 50051
HOST = '0.0.0.0'
USEMONGO = os.getenv("USE_MONGO", "false").lower() == "true"
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017/archiDistriDB")



with open('{}/data/times.json'.format("."), "r") as jsf:
   schedule = json.load(jsf)["schedule"]

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Showtime service!</h1>"
if USEMONGO:
    client = MongoClient(MONGO_URL)
    db = client["archiDistriDB"]
    schedule_collection = db["schedule"]
    if schedule_collection.count_documents({}) == 0:
        with open('{}/data/times.json'.format("."), "r") as jsf:
            initial_schedule = json.load(jsf)["schedule"]
            schedule_collection.insert_many(initial_schedule)
    schedule = list(schedule_collection.find({}))
    for item in schedule:
        item["_id"] = str(item["_id"])

def write(schedule):
    with open('{}/data/times.json'.format("."), 'w') as f:
        full = {}
        full['schedule']=schedule
        json.dump(full, f)
        

@app.route("/schedule", methods=['GET'])
def get_json():
    if USEMONGO:
        schedule = list(schedule_collection.find({}))
        for item in schedule:
            item["_id"] = str(item["_id"])
            
    res = make_response(jsonify(schedule), 200)
    return res

@app.route("/schedule/<dateRequested>", methods=['GET'])
def get_schedule_bydate(dateRequested):
    if USEMONGO:
        schedule = list(schedule_collection.find({}))
        for item in schedule:
            item["_id"] = str(item["_id"])
    
    for itemschedule in schedule:
        if str(itemschedule["date"]) == str(dateRequested):
            res = make_response(jsonify(itemschedule),200)
            return res
    return make_response(jsonify({"error":"Date not found"}),500)

@app.route("/schedule/movies/<movieid>", methods=['GET'])
def get_schedule_bymovieid(movieid):
   json =[]
   if USEMONGO:
        schedule = list(schedule_collection.find({}))
        for item in schedule:
             item["_id"] = str(item["_id"])

   for i in schedule:
      for movie in i["movies"]:
         if str(movie) == str(movieid):
            json.append(i["date"])

   if not json:
      res = make_response(jsonify({"error":"movie title not found"}),500)
   else:
      res = make_response(jsonify(json),200)
   return res

@app.route("/schedule/<dateRequested>", methods=['POST'])
def add_schedule(dateRequested):
    req = request.get_json()
    req["date"] = dateRequested

    if USEMONGO:
        exists = schedule_collection.find_one({"date": dateRequested})
        if exists:
            return make_response(jsonify({"error": "schedule already exists"}), 500)
        schedule_collection.insert_one(req)
        inserted = schedule_collection.find_one({"date": dateRequested})
        inserted["_id"] = str(inserted["_id"])
        return make_response(jsonify({"message": "schedule added", "schedule": inserted}), 200)

    exists = next((s for s in schedule if str(s["date"]) == str(dateRequested)), None)
    if exists:
        return make_response(jsonify({"error": "schedule already exists"}), 500)

    schedule.append(req)
    write(schedule)
    return make_response(jsonify({"message": "schedule added", "schedule": req}), 200)


@app.route("/schedule/<dateRequested>", methods=['DELETE'])
def del_schedule(dateRequested):
    if USEMONGO:
        to_delete = schedule_collection.find_one({"date": dateRequested})
        if not to_delete:
            return make_response(jsonify({"error": "Date requested not found"}), 404)
        schedule_collection.delete_one({"date": dateRequested})
        to_delete["_id"] = str(to_delete["_id"])
        return make_response(jsonify(to_delete), 200)

    for item in schedule:
        if str(item["date"]) == str(dateRequested):
            schedule.remove(item)
            write(schedule)
            return make_response(jsonify(item), 200)

    return make_response(jsonify({"error": "Date requested not found"}), 404)


if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
