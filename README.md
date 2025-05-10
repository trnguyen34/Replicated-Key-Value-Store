# Replicated Key-Value Store
## Mechanisms
### Detecting Downed Replicas 
The system uses a retry mechanism to detect when a replica goes down. When a PUT or DELETE is initiated, the replica broadcasts the new update to  all other replicas in the VIEW. Each request is retried up to three times in case of failure, with a 1-second delay between retires, to account for network issues. If a replica does not respond after three retires, it is considered to be down and removed from the replica's VIEW. Then the replica notifies all remaining replicas to remove the unresponsive replica. 

### Tracking Causal Dependencies
The system tracks causal dependencies using a vector clock mechanism. Each replica maintains a vector clock to track the causal history of processed operations. When a client operates, it includes its vector clock to indicate its causal dependencies. The system checks causal consistency by ensuring that all entries in the client's vector clock are also in the replica's vector clock and that all values must be less or equal to those in the replica's values. Additionally, for PUT and DELETE, the system checks that the client's timestamp for its value is exactly one greater than the value in the replica's vector clock.

## Acknowledgement
- [Vector clock to track causal dependencies](https://www.youtube.com/watch?v=5BHizc7BPyE&t=1s)
- [Causal broadcast for put and delete kvs](https://www.youtube.com/watch?v=buBGyECx69c&list=PLNPUF5QyWU8PydLG2cIJrCvnn5I_exhYx&index=5&t=1318s)
- [Eventual consistency (a liverness property)](https://www.youtube.com/watch?v=InctqJZwCdo&list=PLNPUF5QyWU8PydLG2cIJrCvnn5I_exhYx&index=13&t=391s)
- [Vector Clocks in Distributed Systems](https://www.geeksforgeeks.org/vector-clocks-in-distributed-systems/#)
- [Request Timeout](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts)
