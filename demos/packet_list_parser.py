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

pkts = []
[_pkt.print_packet_detailed(asic_dict, int(pkt)) for pkt in pkts]
print("\n" * 5)


