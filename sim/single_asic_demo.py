import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath("/Users/davidyang/Desktop/larpix-lib"))

import larpix_control.common as common
import asic_classes as ac
from larpix_control.asic.asic_spec import *

def print_break():
    print("_"*30)




v3_spec = asic_spec_from_yaml("config/asics/larpix_v3.yaml")
hw_single = "/Users/davidyang/Desktop/larpix-lib/sim/hw_cfg_ex_two.yaml"

asic_grid = ac.AsicGrid(hw_single, v3_spec)
asic0 = asic_grid.asic_ids[0]
asic1 = asic_grid.asic_ids[1]

# demonstrate correct handling of incorrect chip id
correct_set_id = 0x022541391C2DE806 # set 0x01 (asic0) to 0x0b
wrong_set_id = 0x022541391C2DE82E

asic_grid.send_packets(0, [wrong_set_id])
asic0.print_updated_registers()

asic_grid.send_packets(0, [correct_set_id])
asic0.print_updated_registers()
###

print_break()

# demonstrate correct transmission to second connected asic
asic0_set_ds_pkt = 0x822541391C05F42E # set 125 to 1
asic0_set_us_pkt = 0x022541391C21F02E # set 124 to 8


asic1_set_id_pkt = 0x822541391C31E806 # set 0x01 (asic1) to 0x0c
asic1_set_ds_pkt = 0x022541391C09F432 # set 125 to 2

asic_grid.send_packets(0, [asic0_set_ds_pkt, asic0_set_us_pkt, asic1_set_id_pkt, asic1_set_ds_pkt])

asic0.print_tx_buffers()
asic_grid.update(4) # maximum

asic0.print_updated_registers()
asic1.print_updated_registers()

print_break()

# shouldnt change after more updates
asic_grid.update(1)
asic0.print_updated_registers()
asic1.print_updated_registers()
###


# demonstrate correct read response
asic1_get_id_pkt = 0x822541391C01E833 # get 122 from 0x0c
asic_grid.send_packets(0, [asic1_get_id_pkt])

asic1.print_tx_buffers()

asic_grid.update(4)

# print all packets received by fpga at end
print(asic_grid.received_packets)
###

print("\n" * 3)