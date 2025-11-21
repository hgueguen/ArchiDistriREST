import os
from flask import Flask, request, jsonify, make_response
import json
import sys
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

PORT = 3200
HOST = '0.0.0.0'

USEMONGO = os.getenv("USE_MONGO", "false").lower() == "true"
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017/archiDistriDB")

if USEMONGO:
    client = MongoClient(MONGO_URL)
    db = client["archiDistriDB"]
    movie_collection = db["movies"]
    if movie_collection.count_documents({}) == 0:
        with open('./data/movies.json', 'r') as jsf:
            initial_movies = json.load(jsf)["movies"]
            movie_collection.insert_many(initial_movies)
    movies = []
else:
    with open('./data/movies.json', 'r') as jsf:
        movies = json.load(jsf)["movies"]


def write(movies):
    with open('{}/data/movies.json'.format("."), 'w') as f:
        full = {}
        full['movies'] = movies
        json.dump(full, f)

@app.route("/", methods=['GET'])
def home():
    return make_response("<h1 style='color:blue'>Welcome to the Movie service!</h1>", 200)

@app.route("/json", methods=['GET'])
def get_json():
    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]
        mongo_movies = list(movie_collection.find({}))
        for item in mongo_movies:
            item["_id"] = str(item["_id"])
        return make_response(jsonify(mongo_movies), 200)

    return make_response(jsonify(movies), 200)

@app.route("/movies/<movieid>", methods=['GET'])
def get_movie_byid(movieid):
    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]
        mongo_movies = list(movie_collection.find({}))
        for item in mongo_movies:
            item["_id"] = str(item["_id"])
        for movie in mongo_movies:
            if str(movie.get("id")) == str(movieid):
                return make_response(jsonify(movie), 200)
        return make_response(jsonify({"error": "Movie ID not found"}), 404)

    for movie in movies:
        if str(movie.get("id")) == str(movieid):
            return make_response(jsonify(movie), 200)

    return make_response(jsonify({"error": "Movie ID not found"}), 404)

@app.route("/moviesbytitle", methods=['GET'])
def get_movie_bytitle():
    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]
        movies = list(movie_collection.find({}))

    title = request.args.get("title")
    result = next((m for m in movies if str(m["title"]) == str(title)), None)

    if result:
        if "_id" in result:
            result["_id"] = str(result["_id"])
        return make_response(jsonify(result), 200)
    return make_response(jsonify({"error": "movie title not found"}), 500)

@app.route("/movies/<movieid>", methods=['POST'])
def add_movie(movieid):
    req = request.get_json()

    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]

        exists = movie_collection.find_one({"id": movieid})
        if exists:
            return make_response(jsonify({"error": "movie ID already exists"}), 500)

        req["id"] = movieid
        movie_collection.insert_one(req)
        return make_response(jsonify({"message": "movie added"}), 200)

    exists = next((m for m in movies if str(m["id"]) == str(movieid)), None)
    if exists:
        return make_response(jsonify({"error": "movie ID already exists"}), 500)

    req["id"] = movieid
    movies.append(req)
    write(movies)
    return make_response(jsonify({"message": "movie added"}), 200)

@app.route("/movies/<movieid>/<rate>", methods=['PUT'])
def update_movie_rating(movieid, rate):
    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]

        movie = movie_collection.find_one({"id": movieid})
        if not movie:
            return make_response(jsonify({"error": "movie ID not found"}), 500)

        movie_collection.update_one({"id": movieid}, {"$set": {"rating": int(rate)}})
        movie = movie_collection.find_one({"id": movieid})
        movie["_id"] = str(movie["_id"])
        return make_response(jsonify(movie), 200)

    movie = next((m for m in movies if str(m["id"]) == str(movieid)), None)
    if not movie:
        return make_response(jsonify({"error": "movie ID not found"}), 500)

    movie["rating"] = rate
    write(movies)
    return make_response(jsonify(movie), 200)

@app.route("/movies/<movieid>", methods=['DELETE'])
def del_movie(movieid):
    if USEMONGO:
        client = MongoClient(MONGO_URL)
        db = client["archiDistriDB"]
        movie_collection = db["movies"]

        movie = movie_collection.find_one({"id": movieid})
        if not movie:
            return make_response(jsonify({"error": "Movie ID not found"}), 404)

        movie_collection.delete_one({"_id": movie["_id"]})
        movie["_id"] = str(movie["_id"])
        return make_response(jsonify(movie), 200)

    movie = next((m for m in movies if str(m["id"]) == str(movieid)), None)
    if not movie:
        return make_response(jsonify({"error": "Movie ID not found"}), 404)

    movies.remove(movie)
    write(movies)
    return make_response(jsonify(movie), 200)

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
