# two1 imports
from two1.sell.machine import Two1MachineVirtual
from two1.sell.composer import Two1ComposerContainers
from two1.sell.manager import Two1Manager


class Two1SellClient():
    """ Library client for 21 sell.
    """

    def __init__(self, detected_platform=None, virtual=True, containers=True):
        if detected_platform.detected_os == "Darwin" and \
           virtual is True and containers is True:
            self.manager = Two1Manager(Two1MachineVirtual(), Two1ComposerContainers())
        else:
            raise Exception("This platform and/or configuration "
                            "is not yet supported.")

    def start(self, services, params=None):
        """ Sequence the start of 21 sell services.

        Each method is called and processed, although some system
        configurations just have a pass-through.  Others execute code
        to set up the needed conditions for the next call.

        Args:
            services (list): list of services to start
            params (dict): variables normally acquired via user
                           interaction
        """
        # establish machine layer
        self.manager.start_networking()
        self.manager.create_machine()
        self.manager.start_machine()

        # build container services
        self.manager.build_base_services()
        self.manager.build_market_services(services)

        # start container services
        self.manager.start_services(services)

    def status(self, services):
        """ Get the status of 21 sell services.
        """
        # get base services status
        self.manager.status_router()
        self.manager.status_payments_server()

        # get market services status
        self.manager.status_market_services(services)

    def stop(self, services):
        """ Sequence the stop of 21 sell services.
        """
        # stop container services
        self.manager.stop_services(services)

        # stop machine layer
        self.manager.stop_machine()
        self.manager.delete_machine()
        self.manager.stop_networking()
