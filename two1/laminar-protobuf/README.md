## setup
1.  Use the protobuf directory here to set up protobuf on your system.
Do not download the Github one (This is a slightly modified version of protobuf to make it work with python 3). 
2. Follow the instructions [here](https://github.com/google/protobuf/) to setup protobuf binaries and instructions [here](https://github.com/google/protobuf/tree/master/python) to setup python specific bindings
3. Change the _laminar.proto_ to you liking. [Here](https://developers.google.com/protocol-buffers/docs/proto3) is the reference for protobuf 3 which we use.
4. run ``./generate`` when you are done
5. Pick your language specific classes from the corresponding folder. 

### note
The reason we have the actual protobuf library checked in is that we had to modify it slightly to work with python 3. 
Google is going to fix these issues in the next release (if that doesn't happen we are going to submit a pull request to them). 
Until then the protobuf library should stay in this repo. 

