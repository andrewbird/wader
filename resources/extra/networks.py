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

# --------------------------------------------------------------------------------------------------------#
# ------------------------   Vodafone Opp-Co Network Tables ------------------------#
# --------------------------------------------------------------------------------------------------------#
# -------------------------   Updated: 1/11/2009 --------------------------------------------#
# --------------------------------------------------------------------------------------------------------#

class Vodafone_20205_Contract(NetworkOperator):
    netid = ["20205"]
    name = "Vodafone Greece"
    country = "Greece"
    type = "Contract"
    smsc = "+306942190000"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20205_Prepaid(NetworkOperator):
    netid = ["20205"]
    name = "Vodafone Greece"
    country = "Greece"
    type = "Prepaid"
    smsc = "+306942190000"
    apn = "web.session"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20404_Contract(NetworkOperator):
    netid = ["20404"]
    name = "Vodafone NL"
    country = "Netherlands"
    type = "Contract"
    smsc = "+316540881000"
    apn = "office.vodafone.nl"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_20404_Prepaid(NetworkOperator):
    netid = ["20404"]
    name = "Vodafone NL"
    country = "Netherlands"
    type = "Prepaid"
    smsc = "+316540881000"
    apn = "office.vodafone.nl"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_20601_Contract(NetworkOperator):
    netid = ["20601"]
    name = "Proximus"
    country = "Belgium"
    type = "Contract"
    smsc = "+32475161616"
    apn = "internet.proximus.be"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20601_Prepaid(NetworkOperator):
    netid = ["20601"]
    name = "Proximus"
    country = "Belgium"
    type = "Prepaid"
    smsc = "+32475161616"
    apn = "internet.proximus.be"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20810_Contract(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    type = "Contract"
    smsc = "+33609001390"
    apn = "websfr"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20810_SFR_slsfr(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    type = "SFR slsfr"
    smsc = "+33609001390"
    apn = "slsfr"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20810_SFR_internetpro(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    type = "SFR internetpro"
    smsc = "+33609001390"
    apn = "internetpro"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20810_SFR_ipnet(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    type = "SFR ipnet"
    smsc = "+33609001390"
    apn = "ipnet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_20810_Prepaid(NetworkOperator):
    netid = ["20810"]
    name = "SFR"
    country = "France"
    type = "Prepaid"
    smsc = "+33609001390"
    apn = "websfr"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23801_Contract(NetworkOperator):
    netid = ["23801"]
    name = "TDC Denmark"
    country = "Denmark"
    type = "Contract"
    smsc = "+4540390999"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23801_Prepaid(NetworkOperator):
    netid = ["23801"]
    name = "TDC Denmark"
    country = "Denmark"
    type = "Prepaid"
    smsc = "+4540390999"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_2380171_Contract(NetworkOperator):
    netid = ["2380171"]
    name = "TDC Norway"
    country = "Norway"
    type = "Contract"
    smsc = "+4540390966"
    apn = "internet.no"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_2380171_Prepaid(NetworkOperator):
    netid = ["2380171"]
    name = "TDC Norway"
    country = "Norway"
    type = "Prepaid"
    smsc = "+4540390966"
    apn = "internet.no"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_2380172_Contract(NetworkOperator):
    netid = ["2380172"]
    name = "TDC Sweden"
    country = "Sweden"
    type = "Contract"
    smsc = "+4540390955"
    apn = "internet.se"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_2380172_Prepaid(NetworkOperator):
    netid = ["2380172"]
    name = "TDC Sweden"
    country = "Sweden"
    type = "Prepaid"
    smsc = "+4540390955"
    apn = "internet.se"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24802_Contract(NetworkOperator):
    netid = ["24802"]
    name = "Elisa Estonia"
    country = "Estonia"
    type = "Contract"
    smsc = "+37256100020"
    apn = "internet"
    username = ""
    password = ""
    dns1 = "194.204.0.1"
    dns2 = None

class Vodafone_24802_Prepaid(NetworkOperator):
    netid = ["24802"]
    name = "Elisa Estonia"
    country = "Estonia"
    type = "Prepaid"
    smsc = "+37256100020"
    apn = "internet"
    username = ""
    password = ""
    dns1 = "194.204.0.1"
    dns2 = None

class Vodafone_27801_Contract(NetworkOperator):
    netid = ["27801"]
    name = "Vodafone Malta"
    country = "Malta"
    type = "Contract"
    smsc = "+356941816"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = "80.85.96.131"
    dns2 = "80.85.97.70"

class Vodafone_27801_Prepaid(NetworkOperator):
    netid = ["27801"]
    name = "Vodafone Malta"
    country = "Malta"
    type = "Prepaid"
    smsc = "+356941816"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = "80.85.96.131"
    dns2 = "80.85.97.70"

class Vodafone_50503_Contract(NetworkOperator):
    netid = ["50503"]
    name = "Vodafone Australia"
    country = "Australia"
    type = "Contract"
    smsc = "+61415011501"
    apn = "vfinternet.au"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_50503_Prepaid(NetworkOperator):
    netid = ["50503"]
    name = "Vodafone Australia"
    country = "Australia"
    type = "Prepaid"
    smsc = "+61415011501"
    apn = "vfprepaymbb"
    username = "web"
    password = "web"
    dns1 = None
    dns2 = None

class Vodafone_22210_Contract(NetworkOperator):
    netid = ["22210"]
    name = "vodafone IT"
    country = "Italy"
    type = "Contract"
    smsc = "+393492000200"
    apn = "web.omnitel.it"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_22210_Prepaid(NetworkOperator):
    netid = ["22210"]
    name = "vodafone IT"
    country = "Italy"
    type = "Prepaid"
    smsc = "+393492000200"
    apn = "web.omnitel.it"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23415_Contract(NetworkOperator):
    netid = ["23415"]
    name = "Vodafone UK"
    country = "United Kingdom"
    type = "Contract"
    smsc = "+447785016005"
    apn = "internet"
    username = "web"
    password = "web"
    dns1 = None
    dns2 = None

class Vodafone_23415_Prepaid(NetworkOperator):
    netid = ["23415"]
    name = "Vodafone UK"
    country = "United Kingdom"
    type = "Prepaid"
    smsc = "+447785016005"
    apn = "pp.internet"
    username = "web"
    password = "web"
    dns1 = None
    dns2 = None

class Vodafone_26202_Contract(NetworkOperator):
    netid = ["26202"]
    name = "Vodafone.de"
    country = "Germany"
    type = "Contract"
    smsc = "+491722270333"
    apn = "web.vodafone.de"
    username = ""
    password = ""
    dns1 = "139.7.30.125"
    dns2 = "139.7.30.126"

class Vodafone_26202_WebSession(NetworkOperator):
    netid = ["26202"]
    name = "Vodafone.de"
    country = "Germany"
    type = "WebSession"
    smsc = "+491722270333"
    apn = "event.vodafone.de"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_26202_Corporate(NetworkOperator):
    netid = ["26202"]
    name = "Vodafone.de"
    country = "Germany"
    type = "Corporate"
    smsc = "+491722270333"
    apn = "event.vodafone.de"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_26801_Contract(NetworkOperator):
    netid = ["26801"]
    name = "vodafone P"
    country = "Portugal"
    type = "Contract"
    smsc = "+351911616161"
    apn = "internet.vodafone.pt"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_27201_Contract(NetworkOperator):
    netid = ["27201"]
    name = "Vodafone IE"
    country = "Ireland"
    type = "Contract"
    smsc = "+35387699989"
    apn = "hs.vodafone.ie"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_27201_Prepaid(NetworkOperator):
    netid = ["27201"]
    name = "Vodafone IE"
    country = "Ireland"
    type = "Prepaid"
    smsc = "+35387699989"
    apn = "hs.vodafone.ie"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_21401_Contract(NetworkOperator):
    netid = ["21401"]
    name = "vodafone ES"
    country = "Spain"
    type = "Contract"
    smsc = "+34607003110"
    apn = "ac.vodafone.es"
    username = "vodafone"
    password = "vodafone"
    dns1 = "212.73.32.3"
    dns2 = "212.73.32.67"

class Vodafone_21670_Contract(NetworkOperator):
    netid = ["21670"]
    name = "Vodafone Hungary"
    country = "Hungary"
    type = "Contract"
    smsc = "+36709996500"
    apn = "internet.vodafone.net"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_21670_Prepaid(NetworkOperator):
    netid = ["21670"]
    name = "Vodafone Hungary"
    country = "Hungary"
    type = "Prepaid"
    smsc = "+36709996500"
    apn = "vitamax.internet.vodafone.net"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23201_Contract(NetworkOperator):
    netid = ["23201"]
    name = "A1"
    country = "Austria"
    type = "Contract"
    smsc = "+436640501"
    apn = "A1.net"
    username = "ppp@A1plus.at"
    password = "ppp"
    dns1 = None
    dns2 = None

class Vodafone_65501_Contract(NetworkOperator):
    netid = ["65501"]
    name = "Vodacom"
    country = "South Africa"
    type = "Contract"
    smsc = "+27829129"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_65501_Prepaid(NetworkOperator):
    netid = ["65501"]
    name = "Vodacom"
    country = "South Africa"
    type = "Prepaid"
    smsc = "+27829129"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_27402_Contract(NetworkOperator):
    netid = ["27402"]
    name = "Vodafone Iceland"
    country = "Iceland"
    type = "Contract"
    smsc = "+3546999099"
    apn = "vmc.gprs.is"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_27402_Prepaid(NetworkOperator):
    netid = ["27402"]
    name = "Vodafone Iceland"
    country = "Iceland"
    type = "Prepaid"
    smsc = "+3546999099"
    apn = "vmc.gprs.is"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_45406_Contract(NetworkOperator):
    netid = ["45406"]
    name = "SmarTone-Vodafone"
    country = "Hong Kong"
    type = "Contract"
    smsc = "+85290100000"
    apn = "Internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_27001_Contract(NetworkOperator):
    netid = ["27001"]
    name = "LUXGSM"
    country = "Luxembourg"
    type = "Contract"
    smsc = "+352021100003"
    apn = "web.pt.lu"
    username = ""
    password = ""
    dns1 = "194.154.192.101"
    dns2 = "194.154.192.102"

class Vodafone_27001_Prepaid(NetworkOperator):
    netid = ["27001"]
    name = "LUXGSM"
    country = "Luxembourg"
    type = "Prepaid"
    smsc = "+352021100003"
    apn = "web.pt.lu"
    username = ""
    password = ""
    dns1 = "194.154.192.101"
    dns2 = "194.154.192.102"

class Vodafone_42602_Contract(NetworkOperator):
    netid = ["42602"]
    name = "Zain BH"
    country = "Bahrain"
    type = "Contract"
    smsc = "+97336135135"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_42602_Prepaid(NetworkOperator):
    netid = ["42602"]
    name = "Zain BH"
    country = "Bahrain"
    type = "Prepaid"
    smsc = "+97336135135"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_21910_Contract(NetworkOperator):
    netid = ["21910"]
    name = "Vipnet"
    country = "Croatia"
    type = "Contract"
    smsc = "+385910401"
    apn = "data.vip.hr"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_21910_Prepaid(NetworkOperator):
    netid = ["21910"]
    name = "Vipnet"
    country = "Croatia"
    type = "Prepaid"
    smsc = "+385910401"
    apn = "data.vip.hr"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24405_Contract(NetworkOperator):
    netid = ["24405"]
    name = "Elisa"
    country = "Finland"
    type = "Contract"
    smsc = "+358508771010"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24405_Prepaid(NetworkOperator):
    netid = ["24405"]
    name = "Elisa"
    country = "Finland"
    type = "Prepaid"
    smsc = "+358508771010"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_29340_Contract(NetworkOperator):
    netid = ["29340"]
    name = "Si.mobil"
    country = "Slovenia"
    type = "Contract"
    smsc = "+38640441000"
    apn = "internet.simobil.si"
    username = "simobil"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_29340_Prepaid(NetworkOperator):
    netid = ["29340"]
    name = "Si.mobil"
    country = "Slovenia"
    type = "Prepaid"
    smsc = "+38640441000"
    apn = "internet.simobil.si"
    username = "simobil"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_53001_Contract(NetworkOperator):
    netid = ["53001"]
    name = "Vodafone NZ"
    country = "New Zealand"
    type = "Contract"
    smsc = "+6421600600"
    apn = "www.vodafone.net.nz"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_53001_Prepaid(NetworkOperator):
    netid = ["53001"]
    name = "Vodafone NZ"
    country = "New Zealand"
    type = "Prepaid"
    smsc = "+6421600600"
    apn = "www.vodafone.net.nz"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_60202_Contract(NetworkOperator):
    netid = ["60202"]
    name = "Vodafone Egypt"
    country = "Egypt"
    type = "Contract"
    smsc = "+20105996500"
    apn = "internet.vodafone.net"
    username = "internet"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_60202_Prepaid(NetworkOperator):
    netid = ["60202"]
    name = "Vodafone Egypt"
    country = "Egypt"
    type = "Prepaid"
    smsc = "+20105996500"
    apn = "internet.vodafone.net"
    username = "internet"
    password = "internet"
    dns1 = None
    dns2 = None

class Vodafone_54201_Contract(NetworkOperator):
    netid = ["54201"]
    name = "Vodafone Fiji"
    country = "Fiji"
    type = "Contract"
    smsc = "+679901400"
    apn = "vfinternet.fj"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_54201_Prepaid(NetworkOperator):
    netid = ["54201"]
    name = "Vodafone Fiji"
    country = "Fiji"
    type = "Prepaid"
    smsc = "+679901400"
    apn = "prepay.vfinternet.fj"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28001_Contract(NetworkOperator):
    netid = ["28001"]
    name = "Cytamobile-Vodafone"
    country = "Cyprus"
    type = "Contract"
    smsc = "+35799700000"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28001_Prepaid(NetworkOperator):
    netid = ["28001"]
    name = "Cytamobile-Vodafone"
    country = "Cyprus"
    type = "Prepaid"
    smsc = "+35799700000"
    apn = "pp.internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_22601_Contract(NetworkOperator):
    netid = ["22601"]
    name = "Vodafone RO"
    country = "Romania"
    type = "Contract"
    smsc = "+40722004000"
    apn = "internet.vodafone.ro"
    username = "internet.vodafone.ro"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_22601_Prepaid(NetworkOperator):
    netid = ["22601"]
    name = "Vodafone RO"
    country = "Romania"
    type = "Prepaid"
    smsc = "+40722004000"
    apn = "internet.vodafone.ro"
    username = "internet.vodafone.ro"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_52503_Contract(NetworkOperator):
    netid = ["52503"]
    name = "MobileOne"
    country = "Singapore"
    type = "Contract"
    smsc = "+6596845999"
    apn = "sunsurf"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_52503_Prepaid(NetworkOperator):
    netid = ["52503"]
    name = "MobileOne"
    country = "Singapore"
    type = "Prepaid"
    smsc = "+6596845999"
    apn = "sunsurfmcard"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_27602_Contract(NetworkOperator):
    netid = ["27602"]
    name = "Vodafone Albania"
    country = "Albania"
    type = "Contract"
    smsc = "+355692000200"
    apn = "vodafoneweb"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_27602_Prepaid(NetworkOperator):
    netid = ["27602"]
    name = "Vodafone Albania"
    country = "Albania"
    type = "Prepaid"
    smsc = "+355692000200"
    apn = "vodafoneweb"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23003_Contract(NetworkOperator):
    netid = ["23003"]
    name = "Vodafone CZ"
    country = "Czech Republic"
    type = "Contract"
    smsc = "+420608005681"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23003_Prepaid(NetworkOperator):
    netid = ["23003"]
    name = "Vodafone CZ"
    country = "Czech Republic"
    type = "Prepaid"
    smsc = "+420608005681"
    apn = "ointernet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23003_Corporate(NetworkOperator):
    netid = ["23003"]
    name = "Vodafone CZ"
    country = "Czech Republic"
    type = "Corporate"
    smsc = "+420608005681"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28401_Contract(NetworkOperator):
    netid = ["28401"]
    name = "M-Tel BG"
    country = "Bulgaria"
    type = "Contract"
    smsc = "+35988000301"
    apn = "inet-gprs.mtel.bg"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28401_Prepaid(NetworkOperator):
    netid = ["28401"]
    name = "M-Tel BG"
    country = "Bulgaria"
    type = "Prepaid"
    smsc = "+35988000301"
    apn = "inet-gprs.mtel.bg"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24705_Contract(NetworkOperator):
    netid = ["24705"]
    name = "Bite Latvija"
    country = "Latvia"
    type = "Contract"
    smsc = "+37125850115"
    apn = "Internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24705_Prepaid(NetworkOperator):
    netid = ["24705"]
    name = "Bite Latvija"
    country = "Latvia"
    type = "Prepaid"
    smsc = "+37125850115"
    apn = "Internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24602_Contract(NetworkOperator):
    netid = ["24602"]
    name = "Bite Lietuva"
    country = "Lithuania"
    type = "Contract"
    smsc = "+37069950115"
    apn = "banga"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_24602_Prepaid(NetworkOperator):
    netid = ["24602"]
    name = "Bite Lietuva"
    country = "Lithuania"
    type = "Prepaid"
    smsc = "+37069950115"
    apn = "banga"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_50219_Contract(NetworkOperator):
    netid = ["50219"]
    name = "Celcom Malaysia"
    country = "Malaysia"
    type = "Contract"
    smsc = "+60193900000"
    apn = "celcom3g"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_50219_Prepaid(NetworkOperator):
    netid = ["50219"]
    name = "Celcom Malaysia"
    country = "Malaysia"
    type = "Prepaid"
    smsc = "+60193900000"
    apn = "celcom3g"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_41302_Contract(NetworkOperator):
    netid = ["41302"]
    name = "DIALOG"
    country = "Sri Lanka"
    type = "Contract"
    smsc = "+9477000003"
    apn = "www.dialogsl.com"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_41302_Prepaid(NetworkOperator):
    netid = ["41302"]
    name = "DIALOG"
    country = "Sri Lanka"
    type = "Prepaid"
    smsc = "+9477000003"
    apn = "ppwap"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_22801_Contract(NetworkOperator):
    netid = ["22801"]
    name = "Swisscom"
    country = "Switzerland"
    type = "Contract"
    smsc = "+417949990000"
    apn = "gprs.swisscom.ch"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_22801_Prepaid(NetworkOperator):
    netid = ["22801"]
    name = "Swisscom"
    country = "Switzerland"
    type = "Prepaid"
    smsc = "+417949990000"
    apn = "gprs.swisscom.ch"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28602_Faturali(NetworkOperator):
    netid = ["28602"]
    name = "Vodafone TR"
    country = "Turkey"
    type = "Faturali"
    smsc = "+905429800033"
    apn = "internet"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_28602_Kontorlu(NetworkOperator):
    netid = ["28602"]
    name = "Vodafone TR"
    country = "Turkey"
    type = "Kontorlu"
    smsc = "+905429800033"
    apn = "internet"
    username = "vodafone"
    password = "vodafone"
    dns1 = None
    dns2 = None

class Vodafone_23403_Contract(NetworkOperator):
    netid = ["23403"]
    name = "Airtel-Vodafone"
    country = "Jersey"
    type = "Contract"
    smsc = "+447829791004"
    apn = "airtel-ci-gprs.com"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_23403_Prepaid(NetworkOperator):
    netid = ["23403"]
    name = "Airtel-Vodafone"
    country = "Jersey"
    type = "Prepaid"
    smsc = "+447829791004"
    apn = "airtel-ci-gprs.com"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_73001_Contract(NetworkOperator):
    netid = ["73001"]
    name = "Entel PCS"
    country = "Chile"
    type = "Contract"
    smsc = "+5698890005"
    apn = "imovil.entelpcs.cl"
    username = "entelpcs"
    password = "entelpcs"
    dns1 = None
    dns2 = None

class Vodafone_73001_Prepaid(NetworkOperator):
    netid = ["73001"]
    name = "Entel PCS"
    country = "Chile"
    type = "Prepaid"
    smsc = "+5698890005"
    apn = "imovil.entelpcs.cl"
    username = "entelpcs"
    password = "entelpcs"
    dns1 = None
    dns2 = None

class Vodafone_73001_WebSession(NetworkOperator):
    netid = ["73001"]
    name = "Entel PCS"
    country = "Chile"
    type = "WebSession"
    smsc = "+5698890005"
    apn = "imovil.entelpcs.cl"
    username = "entelpcs"
    password = "entelpcs"
    dns1 = None
    dns2 = None

class Vodafone_73001_Corporate(NetworkOperator):
    netid = ["73001"]
    name = "Entel PCS"
    country = "Chile"
    type = "Corporate"
    smsc = "+5698890005"
    apn = "imovil.entelpcs.cl"
    username = "entelpcs"
    password = "entelpcs"
    dns1 = None
    dns2 = None

class Vodafone_62002_Contract(NetworkOperator):
    netid = ["62002"]
    name = "Vodafone Ghana"
    country = "Ghana"
    type = "Contract"
    smsc = "+233200000007"
    apn = "browse"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_62002_Prepaid(NetworkOperator):
    netid = ["62002"]
    name = "Vodafone Ghana"
    country = "Ghana"
    type = "Prepaid"
    smsc = "+233200000007"
    apn = "browse"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_65101_Contract(NetworkOperator):
    netid = ["65101"]
    name = "Vodacom Lesotho"
    country = "Lesotho"
    type = "Contract"
    smsc = "+26655820088"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_65101_Prepaid(NetworkOperator):
    netid = ["65101"]
    name = "Vodacom Lesotho"
    country = "Lesotho"
    type = "Prepaid"
    smsc = "+26655820088"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_28802_Contract(NetworkOperator):
    netid = ["28802"]
    name = "Vodafone FO"
    country = "Faroe Islands"
    type = "Contract"
    smsc = "+298501440"
    apn = "vmc.vodafone.fo"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_42702_Contract(NetworkOperator):
    netid = ["42702"]
    name = "Vodafone Qatar"
    country = "Qatar"
    type = "Contract"
    smsc = "+9747922222"
    apn = "web.vodafone.com.qa"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_64004_Contract(NetworkOperator):
    netid = ["64004"]
    name = "Vodacom Tanzania"
    country = "Tanzania"
    type = "Contract"
    smsc = "+25575114"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_64004_Prepaid(NetworkOperator):
    netid = ["64004"]
    name = "Vodacom Tanzania"
    country = "Tanzania"
    type = "Prepaid"
    smsc = "+25575114"
    apn = "internet"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40401_Contract(NetworkOperator):
    netid = ["40401"]
    name = "Vodafone India Haryana"
    country = "India"
    type = "Contract"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40401_Prepaid(NetworkOperator):
    netid = ["40401"]
    name = "Vodafone India Haryana"
    country = "India"
    type = "Prepaid"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40405_Contract(NetworkOperator):
    netid = ["40405"]
    name = "Vodafone India Gujarat"
    country = "India"
    type = "Contract"
    smsc = "+919825001002"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40405_Prepaid(NetworkOperator):
    netid = ["40405"]
    name = "Vodafone India Gujarat"
    country = "India"
    type = "Prepaid"
    smsc = "+919825001002"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40411_Contract(NetworkOperator):
    netid = ["40411"]
    name = "Vodafone India Delhi"
    country = "India"
    type = "Contract"
    smsc = "+919811009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40411_Prepaid(NetworkOperator):
    netid = ["40411"]
    name = "Vodafone India Delhi"
    country = "India"
    type = "Prepaid"
    smsc = "+919811009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40413_Contract(NetworkOperator):
    netid = ["40413"]
    name = "Vodafone India Andhra Pradesh"
    country = "India"
    type = "Contract"
    smsc = "+919885005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40413_Prepaid(NetworkOperator):
    netid = ["40413"]
    name = "Vodafone India Andhra Pradesh"
    country = "India"
    type = "Prepaid"
    smsc = "+919885005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40415_Contract(NetworkOperator):
    netid = ["40415"]
    name = "Vodafone India UP East"
    country = "India"
    type = "Contract"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40415_Prepaid(NetworkOperator):
    netid = ["40415"]
    name = "Vodafone India UP East"
    country = "India"
    type = "Prepaid"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40420_Contract(NetworkOperator):
    netid = ["40420"]
    name = "Vodafone India Mumbai"
    country = "India"
    type = "Contract"
    smsc = "+919820005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40420_Prepaid(NetworkOperator):
    netid = ["40420"]
    name = "Vodafone India Mumbai"
    country = "India"
    type = "Prepaid"
    smsc = "+919820005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40427_Contract(NetworkOperator):
    netid = ["40427"]
    name = "Vodafone India Maharashtra and Goa"
    country = "India"
    type = "Contract"
    smsc = "+919823000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40427_Prepaid(NetworkOperator):
    netid = ["40427"]
    name = "Vodafone India Maharashtra and Goa"
    country = "India"
    type = "Prepaid"
    smsc = "+919823000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40430_Contract(NetworkOperator):
    netid = ["40430"]
    name = "Vodafone India Kolkata"
    country = "India"
    type = "Contract"
    smsc = "+919830099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40430_Prepaid(NetworkOperator):
    netid = ["40430"]
    name = "Vodafone India Kolkata"
    country = "India"
    type = "Prepaid"
    smsc = "+919830099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40443_Contract(NetworkOperator):
    netid = ["40443"]
    name = "Vodafone India Tamilnadu"
    country = "India"
    type = "Contract"
    smsc = "+919843000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40443_Prepaid(NetworkOperator):
    netid = ["40443"]
    name = "Vodafone India Tamilnadu"
    country = "India"
    type = "Prepaid"
    smsc = "+919843000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40446_Contract(NetworkOperator):
    netid = ["40446"]
    name = "Vodafone India Kerala"
    country = "India"
    type = "Contract"
    smsc = "+919846000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40446_Prepaid(NetworkOperator):
    netid = ["40446"]
    name = "Vodafone India Kerala"
    country = "India"
    type = "Prepaid"
    smsc = "+919846000040"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40460_Contract(NetworkOperator):
    netid = ["40460"]
    name = "Vodafone India Rajasthan"
    country = "India"
    type = "Contract"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40460_Prepaid(NetworkOperator):
    netid = ["40460"]
    name = "Vodafone India Rajasthan"
    country = "India"
    type = "Prepaid"
    smsc = "+919839099999"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40484_Contract(NetworkOperator):
    netid = ["40484"]
    name = "Vodafone India Chennai"
    country = "India"
    type = "Contract"
    smsc = "+919884005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40484_Prepaid(NetworkOperator):
    netid = ["40484"]
    name = "Vodafone India Chennai"
    country = "India"
    type = "Prepaid"
    smsc = "+919884005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40486_Contract(NetworkOperator):
    netid = ["40486"]
    name = "Vodafone India Karnataka"
    country = "India"
    type = "Contract"
    smsc = "+919886005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40486_Prepaid(NetworkOperator):
    netid = ["40486"]
    name = "Vodafone India Karnataka"
    country = "India"
    type = "Prepaid"
    smsc = "+919886005444"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40488_Contract(NetworkOperator):
    netid = ["40488"]
    name = "Vodafone India Punjab"
    country = "India"
    type = "Contract"
    smsc = "+919888009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40488_Prepaid(NetworkOperator):
    netid = ["40488"]
    name = "Vodafone India Punjab"
    country = "India"
    type = "Prepaid"
    smsc = "+919888009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40566_Contract(NetworkOperator):
    netid = ["40566"]
    name = "Vodafone India UP West"
    country = "India"
    type = "Contract"
    smsc = "+919719009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40566_Prepaid(NetworkOperator):
    netid = ["40566"]
    name = "Vodafone India UP West"
    country = "India"
    type = "Prepaid"
    smsc = "+919719009998"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40567_Contract(NetworkOperator):
    netid = ["40567"]
    name = "Vodafone India West Bengal"
    country = "India"
    type = "Contract"
    smsc = "+919732099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_40567_Prepaid(NetworkOperator):
    netid = ["40567"]
    name = "Vodafone India West Bengal"
    country = "India"
    type = "Prepaid"
    smsc = "+919732099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405750_Contract(NetworkOperator):
    netid = ["405750"]
    name = "Vodafone India Jammu and Kasmir"
    country = "India"
    type = "Contract"
    smsc = "+919796009905"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405750_Prepaid(NetworkOperator):
    netid = ["405750"]
    name = "Vodafone India Jammu and Kasmir"
    country = "India"
    type = "Prepaid"
    smsc = "+919796009905"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405751_Contract(NetworkOperator):
    netid = ["405751"]
    name = "Vodafone India Assam"
    country = "India"
    type = "Contract"
    smsc = "+919706099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405751_Prepaid(NetworkOperator):
    netid = ["405751"]
    name = "Vodafone India Assam"
    country = "India"
    type = "Prepaid"
    smsc = "+919706099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405752_Contract(NetworkOperator):
    netid = ["405752"]
    name = "Vodafone India Bihar"
    country = "India"
    type = "Contract"
    smsc = "+919709099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405752_Prepaid(NetworkOperator):
    netid = ["405752"]
    name = "Vodafone India Bihar"
    country = "India"
    type = "Prepaid"
    smsc = "+919709099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405753_Contract(NetworkOperator):
    netid = ["405753"]
    name = "Vodafone India Orissa"
    country = "India"
    type = "Contract"
    smsc = "+919776099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405753_Prepaid(NetworkOperator):
    netid = ["405753"]
    name = "Vodafone India Orissa"
    country = "India"
    type = "Prepaid"
    smsc = "+919776099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405754_Contract(NetworkOperator):
    netid = ["405754"]
    name = "Vodafone India Himachal Pradesh"
    country = "India"
    type = "Contract"
    smsc = "+919796009905"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405754_Prepaid(NetworkOperator):
    netid = ["405754"]
    name = "Vodafone India Himachal Pradesh"
    country = "India"
    type = "Prepaid"
    smsc = "+919796009905"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405755_Contract(NetworkOperator):
    netid = ["405755"]
    name = "Vodafone India North East"
    country = "India"
    type = "Contract"
    smsc = "+919774099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405755_Prepaid(NetworkOperator):
    netid = ["405755"]
    name = "Vodafone India North East"
    country = "India"
    type = "Prepaid"
    smsc = "+919774099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405756_Contract(NetworkOperator):
    netid = ["405756"]
    name = "Vodafone India Madhya Pradesh"
    country = "India"
    type = "Contract"
    smsc = "+919713099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None

class Vodafone_405756_Prepaid(NetworkOperator):
    netid = ["405756"]
    name = "Vodafone India Madhya Pradesh"
    country = "India"
    type = "Prepaid"
    smsc = "+919713099990"
    apn = "www"
    username = ""
    password = ""
    dns1 = None
    dns2 = None





if __name__ == '__main__':
    print VodafoneSpain()
