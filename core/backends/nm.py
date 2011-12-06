import dbus
from twisted.internet.defer import Deferred
from twisted.python import log
from zope.interface import implements

from wader.common.backends.nm import NetworkManagerBackend as \
    _NetworkManagerBackend
from wader.common.consts import (WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH,
                                 MDM_INTFACE, MM_IP_METHOD_PPP)
from wader.common.interfaces import IBackend

from core.dialer import Dialer

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_OBJPATH = '/org/freedesktop/NetworkManager'
NM_INTFACE = 'org.freedesktop.NetworkManager'
NM_DEVICE = '%s.Device' % NM_INTFACE

NM08_GSM_INTFACE = '%s.Gsm' % NM_DEVICE
NM08_USER_SETTINGS = 'org.freedesktop.NetworkManagerUserSettings'

NM09_MODEM_INTFACE = '%s.Modem' % NM_DEVICE


NM08_STATE = {
    'UNKNOWN': 0,
    'ASLEEP': 1,
    'CONNECTING': 2,
    'CONNECTED': 3,
    'DISCONNECTED': 4,
}

NM09_STATE = {
    'UNKNOWN': 0,
    'ASLEEP': 10,
    'DISCONNECTED': 20,
    'DISCONNECTING': 30,
    'CONNECTING': 40,
    'CONNECTED_LOCAL': 50,
    'CONNECTED_SITE': 60,
    'CONNECTED_GLOBAL': 70,
    'IPCONFIG': 100
}

NM08_DEVICE_STATE_UNKNOWN = 0
NM08_DEVICE_STATE_UNMANAGED = 1
NM08_DEVICE_STATE_UNAVAILABLE = 2
NM08_DEVICE_STATE_DISCONNECTED = 3
NM08_DEVICE_STATE_PREPARE = 4
NM08_DEVICE_STATE_CONFIG = 5
NM08_DEVICE_STATE_NEED_AUTH = 6
NM08_DEVICE_STATE_IP_CONFIG = 7
NM08_DEVICE_STATE_ACTIVATED = 8
NM08_DEVICE_STATE_FAILED = 9

NM08_DEVICE_STATE = {
    'UNKNOWN': NM08_DEVICE_STATE_UNKNOWN,
    'UNMANAGED': NM08_DEVICE_STATE_UNMANAGED,
    'UNAVAILABLE': NM08_DEVICE_STATE_UNAVAILABLE,
    'DISCONNECTED': NM08_DEVICE_STATE_DISCONNECTED,
    'PREPARE': NM08_DEVICE_STATE_PREPARE,
    'CONFIG': NM08_DEVICE_STATE_CONFIG,
    'NEED_AUTH': NM08_DEVICE_STATE_NEED_AUTH,
    'IP_CONFIG': NM08_DEVICE_STATE_IP_CONFIG,
    'ACTIVATED': NM08_DEVICE_STATE_ACTIVATED,
    'FAILED': NM08_DEVICE_STATE_FAILED
}

NM09_DEVICE_STATE_UNKNOWN = 0
NM09_DEVICE_STATE_UNMANAGED = 10
NM09_DEVICE_STATE_UNAVAILABLE = 20
NM09_DEVICE_STATE_DISCONNECTED = 30
NM09_DEVICE_STATE_PREPARE = 40
NM09_DEVICE_STATE_CONFIG = 50
NM09_DEVICE_STATE_NEED_AUTH = 60
NM09_DEVICE_STATE_IP_CONFIG = 70
NM09_DEVICE_STATE_IP_CHECK = 80
NM09_DEVICE_STATE_SECONDARIES = 90
NM09_DEVICE_STATE_ACTIVATED = 100

NM09_DEVICE_STATE = {
    'UNKNOWN': NM09_DEVICE_STATE_UNKNOWN,
    'UNMANAGED': NM09_DEVICE_STATE_UNMANAGED,
    'UNAVAILABLE': NM09_DEVICE_STATE_UNAVAILABLE,
    'DISCONNECTED': NM09_DEVICE_STATE_DISCONNECTED,
    'PREPARE': NM09_DEVICE_STATE_PREPARE,
    'CONFIG': NM09_DEVICE_STATE_CONFIG,
    'NEED_AUTH': NM09_DEVICE_STATE_NEED_AUTH,
    'IP_CONFIG': NM09_DEVICE_STATE_IP_CONFIG,
    'IP_CHECK': NM09_DEVICE_STATE_IP_CHECK,
    'SECONDARIES': NM09_DEVICE_STATE_SECONDARIES,
    'ACTIVATED': NM09_DEVICE_STATE_ACTIVATED
}


class NMDialer(Dialer):
    """I wrap NetworkManager's dialer"""

    def __init__(self, device, opath, **kwds):
        super(NMDialer, self).__init__(device, opath, **kwds)

        self.int = None
        self.conn_obj = None
        self.iface = self._get_stats_iface()
        self.state = self.NM_DISCONNECTED

        self.nm_opath = None
        self.connect_deferred = None
        self.disconnect_deferred = None
        self.sm = None

    def _cleanup(self):
        # enable +CREG notifications afterwards
        self.device.sconn.set_netreg_notification(1)
        self.sm.remove()
        self.sm = None

    def _get_device_opath(self):
        """
        Returns the object path to use in the connection / signal
        """
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        interface = dbus.Interface(obj, NM_INTFACE)
        for opath in interface.GetDevices():
            dev = self.bus.get_object(NM_SERVICE, opath)
            udi = dev.Get('org.freedesktop.NetworkManager.Device', 'Udi')
            if self.device.opath == udi:
                return opath

    def _get_stats_iface(self):
        if self.device.get_property(MDM_INTFACE,
                                    'IpMethod') == MM_IP_METHOD_PPP:
            iface = 'ppp0'  # XXX: shouldn't hardcode to first PPP instance
        else:
            iface = self.device.get_property(MDM_INTFACE, 'Device')

        return iface

    def _on_properties_changed(self, changed):
        if 'State' not in changed:
            return

        if changed['State'] == self.NM_CONNECTED and \
                self.state == self.NM_DISCONNECTED:
            # emit the connected signal and send back the opath
            # if the deferred is present
            self.state = self.NM_CONNECTED
            self.Connected()
            self.connect_deferred.callback(self.opath)
            return

        if changed['State'] == self.NM_DISCONNECTED:

            if self.state == self.NM_CONNECTED:
                self.Disconnected()
                if self.disconnect_deferred is not None:
                    # could happen if we are connected and a NM_DISCONNECTED
                    # signal arrives without having explicitly disconnected
                    self.disconnect_deferred.callback(self.conn_obj)

            if self.state == self.NM_DISCONNECTED:
                # Occurs if the connection attempt failed
                self.Disconnected()
                if self.connect_deferred is not None:
                    msg = 'Network Manager failed to connect'
                    self.connect_deferred.errback(RuntimeError(msg))

            self.state = self.NM_DISCONNECTED
            self._cleanup()

    def _setup_signals(self):
        self.sm = self.bus.add_signal_receiver(self._on_properties_changed,
                                                "PropertiesChanged",
                                                path=self._get_device_opath(),
                                            dbus_interface=self.NM_MODEM_INT)

    def configure(self, config):
        self._setup_signals()
        # get the profile object and obtains its uuid
        # get ProfileManager and translate the uuid to a NM object path
        profiles = self.bus.get_object(WADER_PROFILES_SERVICE,
                                       WADER_PROFILES_OBJPATH)
        # get the object path of the profile being used
        self.nm_opath = profiles.GetNMObjectPath(str(config.uuid),
                                       dbus_interface=WADER_PROFILES_INTFACE)
        # Disable +CREG notifications, otherwise NMDialer won't work
        return self.device.sconn.set_netreg_notification(0)

    def connect(self):
        raise NotImplementedError("Implement in subclass")

    def stop(self):
        self._cleanup()
        return self.disconnect()

    def disconnect(self):
        self.disconnect_deferred = Deferred()
        self.int.DeactivateConnection(self.conn_obj)
        # the deferred will be callbacked as soon as we get a
        # connectivity status change
        return self.disconnect_deferred


class NM08Dialer(NMDialer):

    def __init__(self, device, opath, **kwds):
        self.NM_CONNECTED = NM08_DEVICE_STATE_ACTIVATED
        self.NM_DISCONNECTED = NM08_DEVICE_STATE_DISCONNECTED
        self.NM_MODEM_INT = NM08_GSM_INTFACE

        super(NM08Dialer, self).__init__(device, opath, **kwds)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)

        # NM 0.8 - applet (USER)
        #    <arg name="service_name" type="s" direction="in"/>
        #    <arg name="connection" type="o" direction="in"/>
        #    <arg name="device" type="o" direction="in"/>
        #    <arg name="specific_object" type="o" direction="in"/>
        args = (NM08_USER_SETTINGS,
                self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s\n%s" % args)

        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()


class NM09Dialer(NMDialer):

    def __init__(self, device, opath, **kwds):
        self.NM_CONNECTED = NM09_DEVICE_STATE_ACTIVATED
        self.NM_DISCONNECTED = NM09_DEVICE_STATE_DISCONNECTED
        self.NM_MODEM_INT = NM09_MODEM_INTFACE

        super(NM09Dialer, self).__init__(device, opath, **kwds)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)

        # NM 0.9
        #     <arg name="connection" type="o" direction="in">
        #     <arg name="device" type="o" direction="in">
        #     <arg name="specific_object" type="o" direction="in">
        args = (self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s" % args)

        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()


class NetworkManagerBackend(_NetworkManagerBackend):

    implements(IBackend)

    def get_dialer_klass(self, device):
        if self._get_version() == '08':
            return NM08Dialer
        elif self._get_version() == '084':
            return NM08Dialer
        else:
            return NM09Dialer

nm_backend = NetworkManagerBackend()
