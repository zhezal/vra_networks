A script for generating and applying the configuration of VRA networks according to the jinja2 templates.

The script uses the vlan id from the scope to search for ports to add the configuration to, collects other necessary information from the devices.
According to the collected information, a configuration is generated and applied on network devices.

###### Below is a demonstration of how the script works.

![](demonstration_of_the_script.gif)


- Available commands after running the script:

```python
python vra_cli.py --help

╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ apply                   Apply the VRA network configuration.                                                                                       │
│ create                  Create the VRA network configuration.                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

- Available commands after running the script with the '--create' key

```python
python vra_cli.py create --help

 Usage: vra_cli.py create [OPTIONS]

 Create the VRA network configuration.

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --environment  -e      [TEST|PREVIEW]              [default: None] [required]                                                                   │
│ *  --network      -n      FILENAME                    TXT with IPv4 subnets [default: None] [required]                                             │
│ *  --vlan         -v      INTEGER RANGE [1<=x<=4096]  VLAN ID start value [default: None] [required]                                               │
│ *  --rd           -r      INTEGER                     Route Distinguisher start extended part value [default: None] [required]                     │
│ *  --username     -u      TEXT                        Username for authentication [default: None] [required]                                       │
│ *  --password     -p      TEXT                        Password for authentication [default: None] [required]                                       │
│    --help                                             Show this message and exit.                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

- Available commands after running the script with the '--apply' key:

```python
python vra_cli.py apply --help

 Usage: vra_cli.py apply [OPTIONS]

 Apply the VRA network configuration.

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --username  -u      TEXT  Username for authentication [default: None] [required]                                                                │
│ *  --password  -p      TEXT  Password for authentication [default: None] [required]                                                                │
│    --help                    Show this message and exit.                                                                                           │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
- After running the script with the '--create' key, logs will be output to the console:

```python
─────────────────────────────────────────────────────────── Old configuration files found. ───────────────────────────────────────────────────────────
Find old config in 'generated_vra_configs\TEST-VRA1100' created Fri Aug 11 23:28:43 2023
Find old config in 'generated_vra_configs\TEST-VRA1101' created Fri Aug 11 23:28:43 2023
The program found the old configuration files. Delete or move old configuration files to avoid errors. Delete old configuration files? [y/n] (n): y

──────────────────────────────────────────────────────────── Deleting old configurations ─────────────────────────────────────────────────────────────
[12.08.2023 14:11:24.083] [user1] [INFO] - TEST-VRA1100 - The old configuration was deleted successfully.
[12.08.2023 14:11:24.087] [user1] [INFO] - TEST-VRA1101 - The old configuration was deleted successfully.

────────────────────────────────────── MS-TEST-0001 - Сollecting data to generate configurations for SCOPE_VRA ───────────────────────────────────────
[12.08.2023 14:11:39.429] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] established.
[12.08.2023 14:11:40.916] [user1] [INFO] - MS-TEST-0001 [cisco_ios] - interface Gi1/0 was found based on the search criteria.
[12.08.2023 14:11:41.549] [user1] [INFO] - MS-TEST-0001 [cisco_ios] - interface Po10 was found based on the search criteria.
[12.08.2023 14:11:43.580] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] closed.

─────────────────────────────────────── NX-TEST-01 - Сollecting data to generate configurations for SCOPE_VRA ────────────────────────────────────────
[12.08.2023 14:12:06.892] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] established.
[12.08.2023 14:12:08.132] [user1] [INFO] - NX-TEST-01 [cisco_nxos] - interface Po10 was found based on the search criteria.
[12.08.2023 14:12:08.709] [user1] [INFO] - NX-TEST-01 [cisco_nxos] - interface Eth1/3 was found based on the search criteria.
[12.08.2023 14:12:09.417] [user1] [INFO] - NX-TEST-01 [cisco_nxos] - interface Eth1/4 was found based on the search criteria.
[12.08.2023 14:12:10.049] [user1] [INFO] - NX-TEST-01 [cisco_nxos] - interface Eth1/5 was found based on the search criteria.
[12.08.2023 14:12:12.787] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] closed.

```
- After receiving the necessary information from network devices, the script will show the ports that were found and will configure the configuration for network devices:

```python
SCOPE_VRA
├── MS-TEST-0001
│   ├── Gi1/0 (trunk)
│   └── Po10 (trunk)
└── NX-TEST-01
    ├── Po10 (trunk)
    ├── Eth1/3 (trunk)
    ├── Eth1/4 (trunk)
    └── Eth1/5 (trunk)
```

- After running the script with the '--apply'  key, logs also will be output to the console:
```python
─────────────────────────────────────────────── PREVIEW-VRA2100 - Starting to apply the configuration ────────────────────────────────────────────────
[12.08.2023 14:12:42.484] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] established.
  Applying configuration to MS-TEST-0001 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% Elapsed: 0:00:12 Remaining: 0:00:00

[12.08.2023 14:13:16.933] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] established.
  Applying configuration to NX-TEST-01 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% Elapsed: 0:00:02 Remaining: 0:00:00


─────────────────────────────────────────────── PREVIEW-VRA2101 - Starting to apply the configuration ────────────────────────────────────────────────
[12.08.2023 14:13:19.409] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] intercepted from last SSH session.
  Applying configuration to MS-TEST-0001 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% Elapsed: 0:00:11 Remaining: 0:00:00

[12.08.2023 14:13:30.622] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] intercepted from last SSH session.
  Applying configuration to NX-TEST-01 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% Elapsed: 0:00:01 Remaining: 0:00:00
```

- After applying the configuration, the script checks the state of the interfaces and STP. The script will check the status of the STP ports until they switch to the FWD state.

```python

────────────────────────────────────────────────────── Cheking IPv4 interfaces on MS-TEST-0001 ───────────────────────────────────────────────────────
[12.08.2023 14:13:32.331] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] intercepted from last SSH session.
[12.08.2023 14:13:33.062] [user1] [INFO] - MS-TEST-0001 - Interface Vlan2100 192.168.1.1 has 'up' status, protocol 'up'.
[12.08.2023 14:13:33.699] [user1] [INFO] - MS-TEST-0001 - Interface Vlan2101 192.168.1.129 has 'up' status, protocol 'up'.
┏━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━┓
┃ Interface │ IPv4 address  │ Status │ Protocol ┃
┠───────────┼───────────────┼────────┼──────────┨
┃ Vlan2100  │ 192.168.1.1   │ up     │ up       ┃
┃ Vlan2101  │ 192.168.1.129 │ up     │ up       ┃
┗━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━┛
[12.08.2023 14:13:33.704] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] intercepted from last SSH session.
────────────────────────────────────────────────────────── NX-TEST-01 - Cheking STP state. ───────────────────────────────────────────────────────────
                          vlan id 2101 stp info.
┏━━━━━━━━━━━┯━━━━━━┯━━━━━━━━┯━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┓
┃ Interface │ Role │ Status │ Cost │ Port Priority │ Port ID │ Type       ┃
┠───────────┼──────┼────────┼──────┼───────────────┼─────────┼────────────┨
┃ Po10      │ Root │ FWD    │ 1    │ 128           │ 4105    │ (vPC) P2p  ┃
┃ Eth1/3    │ Desg │ BLK    │ 4    │ 128           │ 3       │ P2p        ┃
┃ Eth1/4    │ Desg │ BLK    │ 4    │ 128           │ 4       │ P2p        ┃
┃ Eth1/5    │ Desg │ BLK    │ 4    │ 128           │ 5       │ P2p        ┃
┗━━━━━━━━━━━┷━━━━━━┷━━━━━━━━┷━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┛
                          vlan id 2100 stp info.
┏━━━━━━━━━━━┯━━━━━━┯━━━━━━━━┯━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┓
┃ Interface │ Role │ Status │ Cost │ Port Priority │ Port ID │ Type       ┃
┠───────────┼──────┼────────┼──────┼───────────────┼─────────┼────────────┨
┃ Po10      │ Root │ FWD    │ 1    │ 128           │ 4105    │ (vPC) P2p  ┃
┃ Eth1/3    │ Desg │ LRN    │ 4    │ 128           │ 3       │ P2p        ┃
┃ Eth1/4    │ Desg │ LRN    │ 4    │ 128           │ 4       │ P2p        ┃
┃ Eth1/5    │ Desg │ LRN    │ 4    │ 128           │ 5       │ P2p        ┃
┗━━━━━━━━━━━┷━━━━━━┷━━━━━━━━┷━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┛

────────────────────────────────────────────────────────── NX-TEST-01 - Cheking STP state. ───────────────────────────────────────────────────────────
                          vlan id 2101 stp info.
┏━━━━━━━━━━━┯━━━━━━┯━━━━━━━━┯━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┓
┃ Interface │ Role │ Status │ Cost │ Port Priority │ Port ID │ Type       ┃
┠───────────┼──────┼────────┼──────┼───────────────┼─────────┼────────────┨
┃ Po10      │ Root │ FWD    │ 1    │ 128           │ 4105    │ (vPC) P2p  ┃
┃ Eth1/3    │ Desg │ FWD    │ 4    │ 128           │ 3       │ P2p        ┃
┃ Eth1/4    │ Desg │ FWD    │ 4    │ 128           │ 4       │ P2p        ┃
┃ Eth1/5    │ Desg │ FWD    │ 4    │ 128           │ 5       │ P2p        ┃
┗━━━━━━━━━━━┷━━━━━━┷━━━━━━━━┷━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┛
                          vlan id 2100 stp info.
┏━━━━━━━━━━━┯━━━━━━┯━━━━━━━━┯━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┓
┃ Interface │ Role │ Status │ Cost │ Port Priority │ Port ID │ Type       ┃
┠───────────┼──────┼────────┼──────┼───────────────┼─────────┼────────────┨
┃ Po10      │ Root │ FWD    │ 1    │ 128           │ 4105    │ (vPC) P2p  ┃
┃ Eth1/3    │ Desg │ FWD    │ 4    │ 128           │ 3       │ P2p        ┃
┃ Eth1/4    │ Desg │ FWD    │ 4    │ 128           │ 4       │ P2p        ┃
┃ Eth1/5    │ Desg │ FWD    │ 4    │ 128           │ 5       │ P2p        ┃
┗━━━━━━━━━━━┷━━━━━━┷━━━━━━━━┷━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┛
[12.08.2023 14:14:09.584] [user1] [INFO] - SSH connection with MS-TEST-0001 [cisco_ios] closed.
[12.08.2023 14:14:09.720] [user1] [INFO] - SSH connection with NX-TEST-01 [cisco_nxos] closed.
Script execution time is 0:01:42.579846
```










