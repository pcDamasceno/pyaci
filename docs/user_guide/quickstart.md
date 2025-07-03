# Quick Start Guide


## Installation

In most cases installation via pip is the simplest and best way to install scrapli.
See [here]() for advanced installation details.

```
pip install scrapli
```


## A Simple Example

```python
from scrapli.driver.core import IOSXEDriver

my_device = {
    "host": "172.18.0.11",
    "auth_username": "scrapli",
    "auth_password": "scrapli",
    "auth_strict_key": False,
}

conn = IOSXEDriver(**my_device)
conn.open()
response = conn.send_command("show run")
print(response.result)
```

```
$ python my_scrapli_script.py
Building configuration...

Current configuration : 7584 bytes
!
! Last configuration change at 19:24:38 PST Sat Feb 29 2020 by carl
! NVRAM config last updated at 19:00:28 PST Fri Feb 7 2020 by carl
!
version 15.2
service nagle
no service pad
service tcp-keepalives-in
service tcp-keepalives-out
service timestamps debug datetime msec
no service password-encryption
!
<SNIP>
!
end
```