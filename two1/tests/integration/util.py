import random
import string

def random_str(length):
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))
