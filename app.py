from flask import Flask, jsonify, request
import requests, os

app = Flask(__name__)

# Corresponds to the current Replica IP address
SOCKET_ADDRESS = os.environ.get('SOCKET_ADDRESS')
# The socket address of the replicas participating the key-value store
VIEW_ADDRESS = os.environ.get('VIEW')

# A dictionary to store key-value pairs 
KV_STORAGE = {}

# A set to store the addresses of replicas in the view
VIEW = set()

# A dictionary to store vector clocks
VECTOR_CLOCKS = {}

# ==================== Utility Functions ====================

# Ensure that the client's vc is less or equal to the to 
# replica's vc. 
def is_causal_consistency(client_vc, replica_vc):
    for client_key in client_vc:
        if client_key not in replica_vc:
            return False

        if client_vc[client_key] > replica_vc[client_key]:
            return False
        
    return True

# ================== End Utility Functions ==================


# ============== VIEW OPERATIONS SECTION =============

@app.route('/view', methods=['PUT'])
def put_replica():
    # Retrieve JSON data from the request
    data = request.get_json()
    # Extract the socket address of the new replica
    new_socket_address = data.get('socket-address')

    # Check if the replica is already in the view
    if new_socket_address in VIEW:
        return jsonify({"result": "already present"}), 200

    # If not present, add the new replica address to the view
    VIEW.add(new_socket_address)
    # Add the new replica to the vc and initialize to 0
    VECTOR_CLOCKS[new_socket_address] = 0

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

# ============== END VIEW OPERATIONS SECTION ===============


# ============== KEY-VALUE OPERATIONS SECTION ==============

@app.route('/kvs/<key>', methods=['PUT'])
def put_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

@app.route('/kvs/<key>', methods=['GET'])
def get_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    if client_vc is None or is_causal_consistency(client_vc, VECTOR_CLOCKS):
        if key in KV_STORAGE:
            value = KV_STORAGE[key]
            return jsonify({"result": "found", "value": value, "causal-metadata": VECTOR_CLOCKS}), 200
        else:
             return jsonify({"error": "Key does not exist"}), 404
    else:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

@app.route('/kvs/<key>', methods=['DELETE'])
def delete_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    # The client's vc is NULL or causal consistency has not been met.
    if client_vc is None or is_causal_consistency(client_vc, VECTOR_CLOCKS) is False:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

    if key not in KV_STORAGE:
        return jsonify({"error": "Key does not exist"}), 404

    del KV_STORAGE[key]    
    # Increment the current replica's vc
    VECTOR_CLOCKS[SOCKET_ADDRESS] += 1

    return jsonify({"result": "deleted", "causal-metadata": VECTOR_CLOCKS}), 200

# ============ END KEY-VALUE OPERATIONS SECTION =============

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8090, debug=True)