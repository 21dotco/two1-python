import random
import string
import subprocess

from two1.bitcoin import crypto

allowed_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + " "


def get_random_string():
    size = random.randrange(1, 200)
    return bytes(''.join(random.choice(allowed_chars) for _ in range(size)), 'ascii')

errors = 0
for i in range(100000):
    # Generate a random private key
    pk = crypto.PrivateKey.from_random()
    address = pk.public_key.address(compressed=False)
    string = get_random_string()

    # Sign the random string
    sig_b64 = pk.sign_bitcoin(string)
    validate_cmd = "bx message-validate %s %s '%s'" % (address, sig_b64.decode('ascii'), string.decode('ascii'))
    retcode = subprocess.call(validate_cmd, shell=True, stdout=subprocess.DEVNULL)
    if retcode:
        errors += 1
        print("%s, return code = %d" % (validate_cmd, retcode))

    sign_cmd = "bx message-sign %s '%s'" % (pk.to_b58check(), string.decode('ascii'))
    bx_sig = subprocess.check_output(sign_cmd, shell=True)[:-1]
    if not crypto.PublicKey.verify_bitcoin(string, bx_sig, address):
        errors += 1
        print("bx sig did not verify for %s" % string)

    if i % 100 == 0:
        print("\rCompleted %d messages." % i)

print("\nTotal number of errors: %d" % (errors))
