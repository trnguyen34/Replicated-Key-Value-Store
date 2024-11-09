from flask import Flask, jsonify, request
import requests, os

app = Flask(__name__)

# A dictionary to store key-value pairs 
KV_STORAGE = {}

# A set to store the addresses of replicas in the view
VIEW = set()

@app.route('/view', methods=['PUT'])
def put_replica():
    # Retrieve JSON data from the request
    data = request.get_json()
    # Extract the socket address of the new replica
    new_socket_address = data.get('socket-address')

    # Check if the replica is already in the view
    if new_socket_address in VIEW:
        return jsonify({"result": "already present"}), 200

    # If not present, add the replica to the view
    VIEW.add(new_socket_address)
    return jsonify({"result": "added"}), 201

@app.route('/view', methods=['GET'])
def get_replicas():
    # Return the current VIEW as a list
    return jsonify({"view": list(VIEW)}), 200

@app.route('/view', methods=['DELETE'])
def delete_replica():
    # Retrieve JSON data from the request
    data = request.get_json()
    # Extract the socket address of the replica to be removed
    socket_address = data.get('socket-address')

     # Check if the replica is in the view
    if socket_address not in VIEW:
         # If not present, respond with an error
        return jsonify({"error": "View has no such replica"}), 404
    
    # If present, remove the replica from the view
    VIEW.remove(socket_address)
    return jsonify({"result": "deleted"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8090, debug=True)