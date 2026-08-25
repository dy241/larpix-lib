import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath("/Users/davidyang/Desktop/larpix-lib"))
import asic_classes as ac

# Copied from init_network

#!/usr/bin/env python3
import sys
from pathlib import Path

from larpix_control import common, asic_spec, asic_spec_from_yaml, fragment_lib_from_yaml, asic_config, hydra_strand, pacman_io_request

verbose = False

asic_s = asic_spec_from_yaml("config/asics/larpix_v3.yaml")
hw_yaml = "/Users/davidyang/Desktop/larpix-lib/sim/hw_cfg_3x1.yaml"
reliability_yaml = "/Users/davidyang/Desktop/larpix-lib/sim/reliability_3x1.yaml"
io_req = ac.BadAsicGrid(hw_yaml, asic_s)

def main():

        frag_lib = fragment_lib_from_yaml("config/fragments/library.yaml", "larpix_v3")
        raw_network = common.dict_from_yaml("config/hydra/3x1.yaml")
        raw_params  = common.dict_from_yaml("config/hydra/parameters.yaml")

        cfg = asic_config(io_req, asic_s, frag_lib, verbose=verbose)
        strand = hydra_strand(raw_network, raw_params, cfg, 0)

        if verbose:
                print("INFO: printing table for hydra strand")
                strand.print_hydra_table()


        if verbose:
                print("INFO: printing grid for hydra strand")
                strand.print_hydra_table()

        strand.reset()

        if verbose:
                print("INFO: printing network state")
                strand.print_network_state()

        strand.init_network()

        if verbose:
                strand.print_network_state()

if __name__ == "__main__":
    main()

def rand_data_pkts(n, pktlen=64): # specific to pkt config for v3 asic
    # generates list of packets with correct ds and parity
    
    import random
    def _parity(num):
        return (bin(num).count("1")) % 2

    def _set_bits(word: int, hi: int, lo: int, value: int) -> int: # from _config_packet
        width = hi - lo + 1
        if value >= (1 << width):
            raise ValueError(f"value {value} does not fit in {width}-bit field [{hi}:{lo}]")
        mask = ((1 << width) - 1) << lo
        return (word & ~mask) | ((value << lo) & mask)

    random.seed()
    pkts = [random.randrange(0, 2 ** pktlen) for _ in range(n)]
    pkts = [_set_bits(p, 1, 0, 1) for p in pkts] # type bits
    pkts = [_set_bits(p, 62, 62, 1) for p in pkts] # downstream bit
    parities = [(1+_parity(p & (2**(pktlen-1)-1))) % 2 for p in pkts]
    pkts = [_set_bits(pkts[idx], 63, 63, parities[idx]) for idx in range(n)]
    return pkts

def print_pkt(pkt):
    print(format(pkt, "#066b"))

# update grid (auto handled by send_packets now)

# open connection (data in) from fpga1 to chip 31
open_listen_all = 0x822541391C3DF886
io_req.asic_ids[6].rx(open_listen_all, -1)
io_req.root_asics[1] = [[6, 'w']]

# set reliabilities here (instead of before hydra init) so the network inits correctly
io_req.set_reliabilities(reliability_yaml)

# send data packets into chip 31, should travel all the way to fpga0
import matplotlib.pyplot as plt
import numpy as np
import time
y = []

start = time.time()
for _ in range(100): # sending 100 * 100 packets on 3x1 takes 0.2s
    data_pkts = rand_data_pkts(100)
    io_req.send_packets(1, data_pkts)
    y.append(len(io_req.received_packets))
    io_req.received_packets = []
stop = time.time()
print(stop-start)
y = np.array(y)
plt.hist(y)
plt.show()

print("\n" * 10)