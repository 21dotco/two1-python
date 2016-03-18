"""Wraps a Wallet object and adds signing capabilities for authentication."""


class MachineAuthWallet(object):
    """Uses Wallet's message signing capability for Auth"""

    def __init__(self, wallet):
        """ Initialize using the provided private_key.

        Args:
            private_key (PrivateKey/str): Private key to use for initializing \
            the object. This can be a PrivateKey object or a base58 \
            encoded string.

        Returns:
            None:
        """
        self.wallet = wallet

    @property
    def public_key(self):
        """Convenience property to retrieve the signing public key."""
        return self.get_public_key()

    def get_public_key(self):
        """Gets the public key that is used for Signing

        Returns:
            PublicKey: PublibKey object
        """
        return self.wallet.get_message_signing_public_key()

    def sign_message(self, message):
        """Signs in provided message using the wallet object.

        Args:
            message (str): Encodes the provided message into UTF-8 before \
                            creating a signature for it.
        Raises:
            TypeError: If the input message is not of type str.

        Returns:
            str: Signature for the message as a base64 encoded string.
                 Returns None if the private_key is None.
        """
        if not isinstance(message, str):
            raise TypeError("Message must be a string")
        return self.wallet.sign_message(message)
