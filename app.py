from flask import Flask, jsonify, request
import requests, os, time

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
VECTOR_CLOCK = {}

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

def is_causal_delivery(client_ip, client_vc, replica_vc):
    if client_ip not in replica_vc:
        return False
    
    if client_vc[client_ip] != (replica_vc[client_ip] + 1):
        return False
    
    for client_key in client_vc:
        if client_key not in replica_vc:
            return False

        if client_key != client_ip:
            if client_vc[client_key] > replica_vc[client_key]:
                return False

    return True

def add_new_replica(new_socket_address):
    # Add the new replica's socket address to the VIEW
    VIEW.add(new_socket_address)

    # Initialize the new replica's vector clock entry to 0.
    VECTOR_CLOCK[new_socket_address] = 0

    print(f"Added replica {new_socket_address} to VIEW and initialized VECTOR_CLOCK.", flush=True)

def broadcast_put_replica(new_socket_address):
    for replica_addr in VIEW:
        if replica_addr != SOCKET_ADDRESS:
            url = f"http://{replica_addr}/viewed"
            json_data = {"socket-address": new_socket_address}

            try:
                response = requests.put(url, json=json_data, timeout=1)
                if response.status_code in (200, 201):
                    print(f"Successfully notified {replica_addr} of new replica {new_socket_address}", flush=True)
                else:
                    print(f"Failed to notify {replica_addr}: {response.status_code}", flush=True)
            except requests.exceptions.RequestException as e:
                print(f"Error notifying {replica_addr}: {e}", flush=True)

def broadcast_delete_replica(socket_address):
    for replica_addr in VIEW:
        if replica_addr != SOCKET_ADDRESS:
            url = f"http://{replica_addr}/viewed"
            json_data = {"socket-address": socket_address}

            try:
                response = requests.delete(url, json=json_data, timeout=1)
                if response.status_code in (200, 401):
                    # break
                    continue
                else:
                    print(f"Failed to notify {replica_addr} to delete replica: {response.status_code}", flush=True)
            except requests.exceptions.RequestException as e:
                print(f"Error notifying {replica_addr} to delete replica: {e}", flush=True)
                

def broadcast_put_kvs(key, value):
    non_response_replicas = []

    for replica_addr in VIEW:
        if replica_addr != SOCKET_ADDRESS:
            url = f"http://{replica_addr}/replica/kvs/{key}/{SOCKET_ADDRESS}"
            json_data = {"value": value, "causal-metadata": VECTOR_CLOCK}
            
            num_retries = 0
            while num_retries < 3:
                try:
                    response = requests.put(url, json=json_data, timeout=1)
                    if response.status_code in (200, 201):
                        print(f"Successfully notified {replica_addr} to put kvs {key}: {value}", flush=True)
                        break
                    else:
                        print(f"Failed to notify {replica_addr} to put kvs {key}: {response.status_code}", flush=True)
                except requests.exceptions.RequestException as e:
                    print(f"Error notifying {replica_addr} to put kvs {key}: {e}", flush=True)
                    num_retries += 1

                print(f"Retrying to notify {replica_addr} to put kvs {key}: {value}", flush=True)
                time.sleep(1)
            
            if num_retries == 3:
                non_response_replicas.append(replica_addr)
    
    for replica_addr in non_response_replicas:
        VIEW.remove(replica_addr)
        broadcast_delete_replica(replica_addr)

def broadcast_delete_kvs(key):
    non_response_replicas = []

    for replica_addr in VIEW:
        if replica_addr != SOCKET_ADDRESS:
            url = f"http://{replica_addr}/replica/kvs/{key}/{SOCKET_ADDRESS}"
            json_data = {"value": value, "causal-metadata": VECTOR_CLOCK}

        num_retries = 0
        while num_retries < 3:
            try:
                response = requests.delete(url, json=json_data, timeout=1)
                if response.status_code in (200, 404):
                    print(f"Successfully notified {replica_addr} to delete kvs {key}: {value}", flush=True)
                    break
                else:
                    print(f"Failed to notify {replica_addr} to delete kvs {key}: {response.status_code}", flush=True)
            except requests.exceptions.RequestException as e:
                print(f"Error notifying {replica_addr} to delete kvs {key}: {e}", flush=True)
                num_retries += 1

            print(f"Retrying to notify {replica_addr} to delete kvs {key}: {value}", flush=True)
            time.sleep(1)
        
        if num_retries == 3:
            non_response_replicas.append(replica_addr)
    
    for replica_addr in non_response_replicas:
        VIEW.remove(replica_addr)
        broadcast_delete_replica(replica_addr)
                
def request_vc_n_kvs():
    global VECTOR_CLOCK
    global KV_STORAGE

    for replica_addr in VIEW:
        if replica_addr != SOCKET_ADDRESS:
            url = f"http://{replica_addr}/vckvs"
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    data = response.json()
                    VECTOR_CLOCK = data.get('vc')
                    KV_STORAGE = data.get('kvs')
                    return 
            except requests.exceptions.RequestException as e:
                print(f"Error requesting vc and kvs from {replica_addr}: {e}", flush=True)
                continue
# ================== End Utility Functions ==================


# ================= REQUEST VECTORCLOCK AND KVS SECTION =================

@app.route('/vckvs', methods=['GET'])
def get_vc_n_kvs():
    return jsonify({'vc': VECTOR_CLOCK, 'kvs': KV_STORAGE}), 200

# ================= REQUEST VECTORCLOCK AND KVS SECTION =================


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

    add_new_replica(new_socket_address)

    broadcast_put_replica(new_socket_address)

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

    broadcast_delete_replica(socket_address)

    return jsonify({"result": "deleted"}), 200

# ============== END VIEW OPERATIONS SECTION ===============


# ============== VIEW OPERATIONS RECEIVED FROM BROADCAST SECTION ===============

@app.route('/viewed', methods=['PUT'])
def put_replica_from_broadcast():
    # Retrieve JSON data from the request
    data = request.get_json()
    # Extract the socket address of the new replica
    new_socket_address = data.get('socket-address')

    # Check if the replica is already in the view
    if new_socket_address in VIEW:
        return jsonify({"result": "already present"}), 200

    add_new_replica(new_socket_address)

    return jsonify({"result": "added"}), 201

@app.route('/viewed', methods=['DELETE'])
def delete_replica_from_broadcast():
    # Retrieve JSON data from the request
    data = request.get_json()
    # Extract the socket address of the new replica
    socket_address = data.get('socket-address')

    # Check if the replica is in the view
    if socket_address not in VIEW:
         # If not present, respond with an error
        return jsonify({"error": "View has no such replica"}), 404

    # If present, remove the replica from the view
    VIEW.remove(socket_address)
    return jsonify({"result": "deleted"}), 200


# ============ END VIEW OPERATIONS RECEIVED FROM BROADCAST SECTION =============


# ============== KEY-VALUE OPERATIONS SECTION ==============

@app.route('/kvs/<key>', methods=['PUT'])
def put_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    if client_vc is not None and is_causal_consistency(client_vc, VECTOR_CLOCK) is False:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

    if 'value' not in data:
        return jsonify({"error": "PUT request does not specify a value"}), 400

    if len(key) > 50:
        return jsonify({"error": "Key is too long"}), 400

    VECTOR_CLOCK[SOCKET_ADDRESS] += 1

    value = data['value']
    broadcast_put_kvs(key, value)

    if key in KV_STORAGE:
        KV_STORAGE[key] = value
        return jsonify({"result": "replaced", "causal-metadata": VECTOR_CLOCK}), 200
    else:
        KV_STORAGE[key] = value
        return jsonify({"result": "created", "causal-metadata": VECTOR_CLOCK}), 201


@app.route('/kvs/<key>', methods=['GET'])
def get_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    if client_vc is None or is_causal_consistency(client_vc, VECTOR_CLOCK):
        if key in KV_STORAGE:
            value = KV_STORAGE[key]
            return jsonify({"result": "found", "value": value, "causal-metadata": VECTOR_CLOCK}), 200
        else:
             return jsonify({"error": "Key does not exist"}), 404
    else:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

@app.route('/kvs/<key>', methods=['DELETE'])
def delete_kvs(key):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    # The client's vc is NULL or causal consistency has not been met.
    if client_vc is None or is_causal_consistency(client_vc, VECTOR_CLOCK) is False:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

    if key not in KV_STORAGE:
        return jsonify({"error": "Key does not exist"}), 404

    del KV_STORAGE[key]    
    # Increment the current replica's vc
    VECTOR_CLOCK[SOCKET_ADDRESS] += 1

    broadcast_delete_kvs(key)

    return jsonify({"result": "deleted", "causal-metadata": VECTOR_CLOCK}), 200

# ============ END KEY-VALUE OPERATIONS SECTION =============


# ============ KEY-VALUE OPERATION RECEIVED FROM BROADCAST SECTION =============

@app.route('/replica/kvs/<key>/<client_ip>', methods=['PUT'])
def put_kvs_from_broadcst(key, client_ip):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    if is_causal_delivery(client_ip, client_vc, VECTOR_CLOCK) is False:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

    VECTOR_CLOCK[client_ip] += 1

    if 'value' not in data:
        return jsonify({"error": "PUT request does not specify a value"}), 400

    if len(key) > 50:
        return jsonify({"error": "Key is too long"}), 400

    value = data['value']
    if key in KV_STORAGE:
        KV_STORAGE[key] = value
        return jsonify({"result": "replaced", "causal-metadata": VECTOR_CLOCK}), 200
    else:
        KV_STORAGE[key] = value
        return jsonify({"result": "created", "causal-metadata": VECTOR_CLOCK}), 201

@app.route('/replica/kvs/<key>/<client_ip>', methods=['DELETE'])
def delete_kvs_from_broadcst(key, client_ip):
    data = request.get_json()
    client_vc = data.get('causal-metadata')

    if is_causal_delivery(client_ip, client_vc, VECTOR_CLOCK) is False:
        return jsonify({"error": "Causal dependencies not satisfied; try again later"}), 503

    VECTOR_CLOCK[client_ip] += 1

    if key not in KV_STORAGE:
        return jsonify({"error": "Key does not exist"}), 404

    del KV_STORAGE[key]
    return jsonify({"result": "deleted", "causal-metadata": VECTOR_CLOCK}), 200

# ============ END KEY-VALUE OPERATION RECEIVED FROM BROADCAST SECTION =============


# ==================== Initialization ====================

# Add the current replica's address 
VIEW.add(SOCKET_ADDRESS)

# Add all addresses from the VIEW_ADDRESS 
for addr in VIEW_ADDRESS.split(','):
    VIEW.add(addr)

# Initialize VECTOR_CLOCK
for replica in VIEW:
    VECTOR_CLOCK[replica] = 0

broadcast_put_replica(SOCKET_ADDRESS)

request_vc_n_kvs()

# ================= End Initialization ====================

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8090, debug=True)