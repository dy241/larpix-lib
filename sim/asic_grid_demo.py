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

def main():
        asic_s = asic_spec_from_yaml("config/asics/larpix_v3.yaml")
        frag_lib = fragment_lib_from_yaml("config/fragments/library.yaml", "larpix_v3")
        raw_network = common.dict_from_yaml("config/hydra/single.yaml")
        raw_params  = common.dict_from_yaml("config/hydra/parameters.yaml")

        # Replaced original (pacman_io_request("config/network/single_local.yaml")) with sim asic_grid
        io_req = ac.ASIC_GRID("config/hydra/single.yaml", asic_s)

        cfg = asic_config(io_req, asic_s, frag_lib, verbose=verbose)
        strand = hydra_strand(raw_network, raw_params, cfg)

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
