import base64
import hashlib

from two1.bitcoin import crypto, script, txn, utils

# Let's create a txn trying to spend one of Satoshi's coins: block 1
# We make the (false) assertion that we own the private key (private_key1)
# and for a raw txn, we put the scriptPubKey associated with that private key
prev_txn_hash = bytes.fromhex('0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098')
prev_script_pub_key = script.Script.build_p2pkh(utils.address_to_key_hash(address1)[1]),
txn_input = txn.TransactionInput(prev_txn_hash,
                                 0,
                                 prev_script_pub_key,
                                 0xffffffff)

# Build the output so that it pays out to address2
txn_output = txn.TransactionOutput(5000000000,
                                   script.Script.build_p2pkh(utils.address_to_key_hash(address2)[1]))

# Create the txn
transaction = txn.Transaction(txn.Transaction.DEFAULT_TRANSACTION_VERSION,
                              [txn_input],
                              [txn_output],
                              0)

# Now sign the txn
transaction.sign([private_key1])

# Dump it out as hex
print("signed txn: %s" % (utils.bytes_to_str(bytes(transaction))))
print("Signed txn: %s" % (transaction))

# Try verifying it very manually - pretend we're doing actual stack operations
stack = []
# Start by pushing the sigScript and publicKey onto the stack
stack.append(bytes.fromhex(transaction.inputs[0].script.ast[0][2:]))
stack.append(bytes.fromhex(transaction.inputs[0].script.ast[1][2:]))

# OP_DUP
stack.append(stack[-1])

# OP_HASH160
pub_key = crypto.PublicKey.from_bytes(stack.pop())
hash160 = pub_key.address[1:]

# OP_EQUALVERIFY - this pub key has to match the one in the previous tx output.
assert pub_key.b58address == address1

# OP_CHECKSIG
# Here we need to restructure the txn
pub_key_dup = stack.pop()
script_sig_complete = stack.pop()
script_sig, hash_code_type = script_sig_complete[:-1], script_sig_complete[-1]

new_txn_input = txn.TransactionInput(prev_txn_hash,
                                     0,
                                     script.Script.build_p2pkh(hash160),
                                     0xffffffff)

new_txn = txn.Transaction(txn.Transaction.DEFAULT_TRANSACTION_VERSION,
                          [new_txn_input],
                          [txn_output],
                          0)

new_txn_bytes = bytes(new_txn)

# Now verify
sig = crypto.Signature.from_der(script_sig)
assert pub_key.verify(utils.dhash(new_txn_bytes + utils.pack_u32(hash_code_type)), sig)

assert not pub_key.verify(utils.dhash(new_txn_bytes), sig)
