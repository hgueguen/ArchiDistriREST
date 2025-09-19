from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3202
HOST = '0.0.0.0'

with open('{}/databases/times.json'.format("."), "r") as jsf:
   schedule = json.load(jsf)["schedule"]

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Showtime service!</h1>"


def write(schedule):
    with open('{}/databases/times.json'.format("."), 'w') as f:
        full = {}
        full['schedule']=schedule
        json.dump(full, f)
        

@app.route("/schedule", methods=['GET'])
def get_json():
    res = make_response(jsonify(schedule), 200)
    return res

@app.route("/schedule/<dateRequested>", methods=['GET'])
def get_schedule_bydate(dateRequested):
    for itemschedule in schedule:
        if str(itemschedule["date"]) == str(dateRequested):
            res = make_response(jsonify(itemschedule),200)
            return res
    return make_response(jsonify({"error":"Date not found"}),500)

@app.route("/schedule/movies/<movieid>", methods=['GET'])
def get_schedule_bymovieid(movieid):
   json =[]
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

    for time in schedule:
        if str(time["date"]) == str(dateRequested):
            print(time["date"])
            print(dateRequested)
            return make_response(jsonify({"error":"schedule already exists"}),500)

    schedule.append(req)
    write(schedule)
    res = make_response(jsonify({"message":"schedule added"}),200)
    return res

@app.route("/schedule/<dateRequested>", methods=['DELETE'])
def del_schedule(dateRequested):
    for time in schedule:
        if str(time["date"]) == str(dateRequested):
            schedule.remove(time)
            write(schedule)
            return make_response(jsonify(time),200)

    res = make_response(jsonify({"error":"movie ID not found"}),500)
    return res


if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
