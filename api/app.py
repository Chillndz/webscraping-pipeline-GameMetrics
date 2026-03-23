from flask import Flask, jsonify
import json

app = Flask(__name__)

# Charger les données
def load_data():
    with open("../data/raw_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def home():
    return {"message": "GameMetrics API running"}

@app.route("/games", methods=["GET"])
def get_games():
    data = load_data()
    return jsonify(data)


@app.route("/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    data = load_data()
    
    if game_id < len(data):
        return jsonify(data[game_id])
    
    return {"error": "Game not found"}, 404




if __name__ == "__main__":
    app.run(debug=True)

