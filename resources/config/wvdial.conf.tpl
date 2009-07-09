[Dialer Defaults]

Phone = *99***1#
Username = $username
Password = $password
Stupid Mode = 1
Dial Command = ATDT
New PPPD = yes
Check Def Route = on
Dial Attempts = 3

[Dialer connect]

Modem = $serialport
Baud = 460800
Init2 = ATZ
Init3 = ATQ0 V1 E0 S0=0 &C1 &D2 +FCLASS=0
Init4 = AT+CGDCONT=1,"IP","$apn"
ISDN = 0
Modem Type = Analog Modem
