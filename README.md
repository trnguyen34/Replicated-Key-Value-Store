# CSE138_Assignment3

## Mechanisms
### Detecting Downed Replicas 
The system uses a retry mechanism to detect when a replica goes down. When a PUT or DELETE is initiated, the replica broadcasts the new update to  all other replicas in the VIEW. Each request is retied up to three times in case of failure, with a 1 second delay between retires, to account for network issues. IF a replica does not repond adter three retires, it is considered to be down and removed from the replica's VIEW. Then the replica notfy all renmaining replicas to remove the unreponsive replica. 

### Tracking Causal Dependencies
The system tracks causal dependencies using a vector clock mechanism. Each replica maintains a vector clock to tracks the causal history of ioerations it has processed. When a client performs an operation, it includes its vector clock to indicate its causal dependencies. The system checks causal consistency by ensuring that all entries in the client's vector clock are also in the replica's vector clock and the all values must be be less or equal to the values in relica's values. Additionally, for PUT and DELETE, the system checks that the client's timestamp for its own value is exactly one greater than the the value in the replica's vector clock.

## Acknowledgement
- [Vector clock to track causal dependencies](https://www.youtube.com/watch?v=5BHizc7BPyE&t=1s)
- [Causal broadcast for put and delete kvs](https://www.youtube.com/watch?v=buBGyECx69c&list=PLNPUF5QyWU8PydLG2cIJrCvnn5I_exhYx&index=5&t=1318s)
- [Eventual consistency (a liverness property)](https://www.youtube.com/watch?v=InctqJZwCdo&list=PLNPUF5QyWU8PydLG2cIJrCvnn5I_exhYx&index=13&t=391s)
