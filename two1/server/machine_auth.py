"""Uses a PrivateKey to provide signing capabilities for authentication."""
import keyring
from two1.bitcoin.crypto import PrivateKey


class MachineAuth(object):
    """ Manages the PrivateKey used for signing requests to the TwentyOne Server.

    Attributes:
        private_key (PrivateKey): Uses a Private key based on the Bitcoin \
        elleptic curve.
        public_key (PublicKey): Corresponding Public key.
    """

    def __init__(self, private_key):
        """ Initialize using the provided private_key.

        Args:
            private_key (PrivateKey/str): Private key to use for initializing \
            the object. This can be a PrivateKey object or a base58 \
            encoded string.

        Returns:
            None:
        """
        if private_key:
            if isinstance(private_key, str):  # base58 encoded string
                self.private_key = PrivateKey.from_b58check(private_key)
            else:
                self.private_key = private_key
            self.public_key = self.private_key.public_key
        else:
            self.private_key = None
            self.public_key = None

    @staticmethod
    def from_keyring():
        """ Initializes the object using the private_key stored in the keyring.

        Returns:
            MachineAuth: Constructed MachineAuth object if the auth_key exists.
            Returns None if the auth key is not found in the keyring.
        """
        existing_key = keyring.get_password("twentyone", "mining_auth_key")
        if existing_key:
            return MachineAuth(existing_key)
        else:
            return None

    @staticmethod
    def from_random():
        """ Initializes the object using a random private_key.
            The private key is generated using the system entropy source.

        Returns:
            MachineAuth: Constructed MachineAuth object.
            Returns None if the auth key is not found in the keyring.
        """
        auth_key = PrivateKey.from_random()
        return MachineAuth(auth_key)

    def get_public_key(self):
        """ Gets the public key object corresponding to the private key

        Returns:
            PublicKey: PublibKey object
        """
        return self.public_key

    def saveto_keyring(self):
        """ Saves the private key in the keyring (available on the system).

        Raises:
            ValueError: If the private is not set.

        Returns:
            bool: True if the key was saved successfully, False otherwise.
        """
        if self.private_key:
            auth_key_b58 = self.private_key.to_b58check()
            try:
                keyring.set_password(
                    "twentyone", "mining_auth_key", auth_key_b58)
                return True
            except keyring.errors.PasswordSetError:
                return False
        else:
            raise ValueError("Private key is not set.")

    def sign_message(self, message):
        """ Signs in privded message using the private key and returns the signature.

        Args:
            message (str): Encodes the provided message into UTF-8 before \
                            creating a signature for it.
        Raises:
            ValueError: If the input message is not of type str.

        Returns:
            str: Signature for the message as a base64 encoded string.
                 Returns None if the private_key is None.
        """
        if self.private_key:
            if isinstance(message, str):
                utf8 = message.encode('utf-8')
            else:
                raise TypeError("message must be a string.")
            signature = self.private_key.sign(utf8).to_base64()
            return signature
        else:
            return None
