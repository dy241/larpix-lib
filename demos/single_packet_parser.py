# thomas's code

#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root (one level up from daq/) to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# test/test_config_packet_helpers.py
import unittest

import larpix_control.common as common
import larpix_control.asic._config_packet as _pkt
import larpix_control.asic.asic_spec as _as

asic_spec = _as.asic_spec_from_yaml("/Users/davidyang/Desktop/larpix-lib/config/asics/larpix_v3.yaml")
asic_dict = asic_spec.asic_dict
_pkt.validate_config_packet_dict(asic_dict,verbose=True)

chip = 0x01
# us, ds, listen is 124, 125, 126, chip_id is 122
addr = 122
value = 0x0c

print(f"*** creating write packet from provided values: ***")
print(f"INFO chip:  {chip}  addr:  {addr}  value: {value}")
packet = _pkt.build_config_write(asic_dict, chip, addr, value)
print(f"Write packet:  0x{packet:016X}")
_pkt.print_packet_detailed(asic_dict, packet)

print(f"*** creating confirmation read packet from provided values: ***")
print(f"INFO chip:  {chip}  addr:  {addr}")
packet = _pkt.build_config_read(asic_dict, chip, addr)
print(f"Read packet:  0x{packet:016X}")
_pkt.print_packet_detailed(asic_dict, packet)


print(f"*** intepreting packet from provide value: ***")
#pkt = 0x422541391C2DE82F
pkt = 0xC22541391C09F82F
print(f"packet:  0x{pkt:016X}")
_pkt.print_packet_detailed(asic_dict, pkt)


