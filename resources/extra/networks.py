# network operator list database
# if you need to add a new NetworkOperator do it here. If
# your network does not require a username/password, the convention
# is to use '*' as a dummy value, might not work otherwise.

class NetworkOperator(object):
    netid = []
    name = None
    country = None
    apn = None
    username = None
    password = None
    dns1 = None
    dns2 = None
    smsc = None
    mmsc = None
    type = 1

    def __repr__(self):
        args = (self.name, self.country, self.netid[0])
        return "<NetworkOperator %s%s netid: %s>" % args


class SFRFrance(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    apn = "websfr"
    username = "websfr"
    password = "websfr"
    dns1 = "172.20.2.10"
    dns2 = "194.6.128.4"


class VodafoneSpain(NetworkOperator):
    netid = ["21401"]
    name = "Vodafone"
    country = "Spain"
    apn = "ac.vodafone.es"
    username = "vodafone"
    password = "vodafone"
    dns1 = "212.73.32.3"
    dns2 = "212.73.32.67"


class MovistarSpain(NetworkOperator):
    netid = ["21402", "21407"]
    name = "Movistar"
    country = "Spain"
    apn = "movistar.es"
    username = "movistar"
    password = "movistar"
    dns1 = "194.179.1.100"
    dns2 = "194.179.1.101"


class YoigoSpain(NetworkOperator):
   netid = ["21403", "21404"]
   name = "Yoigo"
   country = "Spain"
   apn = "internet"
   username = "yoigo"
   password = "yoigo"
   dns1 = "10.8.0.20"
   dns2 = "10.8.0.21"


class SimyoSpain(NetworkOperator):
    netid = ["21419"]
    name = "Simyo"
    country = "Spain"
    apn = "gprs-service.com"
    username = "*"
    password = "*"
    dns1 = "217.18.32.170"
    dns2 = "217.18.32.170"


class VIPCroatia(NetworkOperator):
    netid = ["21910"]
    name = "VIP"
    country = "Croatia"
    apn = "data.vip.hr"
    username = "38591"
    password = "38591"
    dns1 = "212.91.97.3"
    dns2 = "212.91.97.4"


class VodacomSouthAfrica(NetworkOperator):
    netid = ["65501"]
    name = "Vodacom"
    country = "South Africa"
    apn = "internet"
    username = "vodafone"
    password = "vodafone"
    dns1 = "196.207.32.69"
    dns2 = "196.43.1.11"


class VodafoneAustralia(NetworkOperator):
    netid = ["50503"]
    name = "Vodafone"
    country = "Australia"
    apn = "vfinternet.au"
    username = "*"
    password = "*"
    dns1 = None
    dns2 = None


class VodafoneItaly(NetworkOperator):
    netid = ["22210"]
    name = "Vodafone"
    country = "Italy"
    apn = "web.omnitel.it"
    username = "vodafone"
    password = "vodafone"
    dns1 = "83.224.65.134"
    dns2 = "83.224.66.234"


class VodafonePortugal(NetworkOperator):
    netid = ["26801"]
    name = "Vodafone"
    country = "Portugal"
    apn = "internet.vodafone.pt"
    username = "vodafone"
    password = "vodafone"
    dns1 = "212.18.160.133"
    dns2 = "212.18.160.134"


class VodafoneNetherlands(NetworkOperator):
    netid = ["20404"]
    name = "Vodafone"
    country = "Netherlands"
    apn = "live.vodafone.com"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None


class VodafoneGermany(NetworkOperator):
    netid = ["26202"]
    name = "Vodafone"
    country = "Germany"
    apn = "web.vodafone.de"
    username = "vodafone"
    password = "vodafone"
    dns1 = "139.7.30.125"
    dns2 = "139.7.30.126"


class NetComNorway(NetworkOperator):
    netid = ["24202"]
    name = "NetCom"
    country = "Norway"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = "212.169.123.67"
    dns2 = "212.45.188.254"


class MobileOneSingapore(NetworkOperator):
    netid = ["52503"]
    name = "MobileOne"
    country = "Singapore"
    apn = "sunsurf"
    username = "M1"
    password = "M1"
    dns1 = "202.65.247.151"
    dns2 = "202.65.247.151"


class TelkomSelIndonesia(NetworkOperator):
    netid = ["51010"]
    name = "TelkomSel"
    country = "Indonesia"
    apn = "flash"
    username = "flash"
    password = "flash"
    dns1 = "202.3.208.10"
    dns2 = "202.3.210.10"


class SATelindoIndonesia(NetworkOperator):
    netid = ["51001"]
    name = "PT. SATelindo C"
    country = "Indonesia"
    apn = "indosat3g"
    username = "indosat"
    password = "indosat"
    dns1 = "202.155.46.66"
    dns2 = "202.155.46.77"


class IM3Indonesia(NetworkOperator):
    netid = ["51021"]
    name = "IM3"
    country = "Indonesia"
    apn = "www.indosat-m3.net"
    username = "im3"
    password = "im3"
    dns1 = "202.155.46.66"
    dns2 = "202.155.46.77"


class O2UK(NetworkOperator):
    netid = ["23411"]
    name = "O2"
    country = "UK"
    apn = "mobile.o2.co.uk"
    username = "o2web"
    password = "password"
    dns1 = "193.113.200.200"
    dns2 = "193.113.200.201"


class OrangeUK(NetworkOperator):
    netid = ["23433","23434"]
    name = "Orange"
    country = "UK"
    apn = "orangeinternet"
    username = "web"
    password = "web"
    dns1 = "158.43.192.1"
    dns2 = "158.43.128.1"


class ProXLndonesia(NetworkOperator):
    netid = ["51011"]
    name = "Pro XL"
    country = "Indonesia"
    apn = "www.xlgprs.net"
    username = "xlgprs"
    password = "proxl"
    dns1 = "202.152.254.245"
    dns2 = "202.152.254.246"


class TMNPortugal(NetworkOperator):
    netid = ["26806"]
    name = "TMN"
    country = "Portugal"
    apn = "internet"
    username = "tmn"
    password = "tmnnet"
    dns1 = None
    dns2 = None


class ThreeItaly(NetworkOperator):
    netid = ["22299"]
    name = "3"
    country = "Italy"
    apn = "naviga.tre.it"
    username = "anon"
    password = "anon"
    dns1 = "62.13.171.1"
    dns2 = "62.13.171.2"


class ThreeAustralia(NetworkOperator):
    netid = ["50503"]
    name = "3"
    country = "Australia"
    apn = "3netaccess"
    username = "*"
    password = "*"
    dns1 = None
    dns2 = None


class ThreeUK(NetworkOperator):
    netid = ["23420"]
    name = "3"
    country = "UK"
    apn = "3internet"
    username = "three"
    password = "three"
    dns1 = "172.31.76.69"
    dns2 = "172.31.140.69"


class TMobileUK(NetworkOperator):
    netid = ["23430", "23431", "23432"]
    name = "T-Mobile"
    country = "UK"
    apn = "general.t-mobile.uk"
    username = "*"
    password = "*"
    dns1 = "149.254.192.126"
    dns2 = "149.254.201.126"


class TimItaly(NetworkOperator):
    netid = ["22201"]
    name = "TIM"
    country = "Italy"
    apn = "ibox.tim.it"
    username = "anon"
    password = "anon"
    dns1 = None
    dns2 = None


class WindItaly(NetworkOperator):
    netid = ["22288"]
    name = "Wind"
    country = "Italy"
    apn = "internet.wind"
    username = "anon"
    password = "anon"
    dns1 = None
    dns2 = None


class ChinaMobile(NetworkOperator):
    netid = ["46000"]
    name = "China Mobile"
    country = "China"
    apn = "cmnet"
    username = "zte"
    password = "zte"
    dns1 = None
    dns2 = None


class OmnitelLithuania(NetworkOperator):
    netid = ["24601"]
    name = "Omnitel"
    country = "Lithuania"
    apn = "omnitel"
    username = "omni"
    password = "omni"
    dns1 = None
    dns2 = None


class BiteLithuania(NetworkOperator):
    netid = ["24602"]
    name = "Bite"
    country = "Lithuania"
    apn = "banga"
    username = "*"
    password = "*"
    dns1 = None
    dns2 = None


class Tele2Lithuania(NetworkOperator):
    netid = ["24603"]
    name = "Tele2"
    country = "Lithuania"
    apn = "internet.tele2.lt"
    username = "wap"
    password = "wap"
    dns1 = "130.244.127.161"
    dns2 = "130.244.127.169"


class UnitelAngola(NetworkOperator):
    netid = ["63102"]
    name = "Unitel"
    country = "Angola"
    apn = "internet.unitel.co.ao"
    username = "*"
    password = "*"
    dns1 = None
    dns2 = None


if __name__ == '__main__':
    print VodafoneSpain()
