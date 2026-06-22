# dont need this file

#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root (one level up from daq/) to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# test/test_config_packet_helpers.py
import unittest

import larpix_control.common as common
import larpix_control.asic._config_packet as _pkt

asic_dict = common.dict_from_yaml("config/asics/larpix_v3.yaml")
_pkt.validate_config_packet_dict(asic_dict,verbose=True)

def _tx():
    chip = 0xB
    addr = 126
    value = 0xf

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

def parse_packet(pkt):
    parsed = _pkt.parse_config_packet_fields(asic_dict, pkt)

    chip  = parsed.get("chip", 0)
    addr  = parsed.get("addr", 0)
    value = parsed.get("value", 0)

    return chip, addr, value
    
