import larpix_control.asic._config_packet as _pkt
import larpix_control.common as common
from larpix_control import asic_spec, asic_spec_from_yaml, fragment_lib_from_yaml, asic_config, hydra_strand, pacman_io_request
from larpix_control.common.interfaces import io_request_iface
import sim._asic_helper as _as
import numpy as np

import copy
import time
from collections import deque

def hexify(num):
    # return a 8 byte padded hex string given an int
    # https://stackoverflow.com/questions/12638408/decorating-hex-function-to-pad-zeros
    return f"{num:#0{10}x}"

class ASIC:
    # class attributes

    def __init__(self, asic_spec):
        # instance attributes
        # needs to "know" what it's connected to
        # default chip id, depending on version
        # default registers, depending on version
        # keep track of enabled us/ds (technically can get directly from registers but could be nice to have for debugging)
        
        self.asic_spec = asic_spec
        self.reg_size = self.asic_spec.get_reg_size()
        self.num_registers = self.asic_spec.get_num_registers()
        self.num_ports = self.asic_spec.num_ports()

        self.field_to_reg = self.asic_spec.get_field_to_reg_lut()
        self.reg_to_field = self.asic_spec.get_reg_to_field_lut()
        self.field_to_reset_value = self.asic_spec.get_field_to_reset_value_lut()
        
        # initialize registers based on spec in config
        self.reset_registers = _as.all_registers_reset_value(self.field_to_reg, self.field_to_reset_value, self.num_registers)
        self.registers = [0x0] * self.num_registers

        self.tx_buffers = [deque() for _ in range(self.num_ports)] # fifos/queues
        self.reset()

        # set useful attributes
        # also need the in/out map to know what channel to receive on, get from asic_spec.params

    def _get_chip_id(self): # move this+get_enables to asic_helper
        reg, width, offset, mask = self.field_to_reg[f"chip_id"]
        chip_id_reg_val = self.registers[reg]
        chip_id = (chip_id_reg_val & mask) >> offset
        return chip_id

    def _get_downstream_enables(self):
        ds_enables = [None] * self.num_ports
        for idx in range(self.num_ports):
            reg, width, offset, mask = self.field_to_reg[f"enable_piso_downstream[{idx}]"]
            ds_reg_val = self.registers[reg]
            ds = (ds_reg_val & mask) >> offset
            ds_enables[idx] = ds
        return ds_enables
    
    def _get_upstream_enables(self):
        us_enables = [None] * self.num_ports
        for idx in range(self.num_ports):
            reg, width, offset, mask = self.field_to_reg[f"enable_piso_upstream[{idx}]"]
            us_reg_val = self.registers[reg]
            us = (us_reg_val & mask) >> offset
            us_enables[idx] = us
        return us_enables
    
    def _get_listen_enables(self):
        listen_enables = [None] * self.num_ports
        for idx in range(self.num_ports):
            reg, width, offset, mask = self.field_to_reg[f"enable_posi[{idx}]"]
            listen_reg_val = self.registers[reg]
            listen = (listen_reg_val & mask) >> offset
            listen_enables[idx] = listen
        return listen_enables

    def _set_register(self, reg, width, offset, val):
        # TODO: check if bits or val exceed register size
        if reg >= self.num_registers:
            print("register out of range")
            return
        if val >= 2 ** self.reg_size:
            print("trying to set value larger than register size")
        reg_val = self.registers[reg]
        val = val * 2 ** offset
        val = val % (2 ** self.reg_size)
        mask = 2 ** (width + offset) - 2 ** offset # ones where bits should be replaced
        reg_val = reg_val & (~mask & 255) # TODO: replace with 2 ** regsize - 1
        reg_val = reg_val | val
        self.registers[reg] = reg_val

    # methods
    def reset(self):
        self.registers = copy.deepcopy(self.reset_registers)

    def rx(self, packet:int, channel:int): 
        # TODO: document (and move to helper)
        # check if listening on channel
        if (channel >= 0) and (not self._get_listen_enables()[channel]): # ignore listen check if channel is -1 (for debugging)
            return
        
        chip, addr, val = self.asic_spec.parse_chip_address_value(packet)
        if chip == self._get_chip_id():
            if self.asic_spec.valid_config_read_request(packet):
                response_val = self.registers[addr]
                response_packet = self.asic_spec.build_config_packet(chip, addr, response_val, downstream=1, write=False)
                self._add_packet_to_buffers(response_packet)
            elif self.asic_spec.valid_config_read_response(packet):
                self._add_packet_to_buffers(packet)
            elif self.asic_spec.valid_config_write(packet):
                self._set_register(addr, 8, 0, val)
        else:
            # "not for me"
            self._add_packet_to_buffers(packet)

    def _add_packet_to_buffers(self, packet):
        buffer_idxs = [0] * self.num_ports # if not valid, dont add to any buffers
        if self.asic_spec.valid_downstream_packet(packet):
            # send downstream
            buffer_idxs = self._get_downstream_enables()
        elif self.asic_spec.valid_upstream_packet(packet):
            # send upstream
            buffer_idxs = self._get_upstream_enables()
        for i in range(self.num_ports):
            if buffer_idxs[i]:
                self.tx_buffers[i].append(packet)
        
    
    def tx(self, channel):
        if self.tx_empty(channel):
            raise Exception(f"{self}'s tx_buffer[{channel}] is empty")
        return self.tx_buffers[channel].popleft()
    
    def tx_empty(self, channel):
        return len(self.tx_buffers[channel]) == 0

    def tx_all_empty(self):
        return all([self.tx_empty(channel) for channel in range(self.num_ports)])

    # debugging tools
    def print_register(self, register_num):
        print(hex(self.registers[register_num]))

    def print_all_registers(self):
        for i in range(self.num_registers):
            print(i, hex(self.registers[i]), "\n")

    def print_updated_registers(self):
        any_updates = False
        for i in range(self.num_registers):
            if self.registers[i] != self.reset_registers[i]:
                any_updates = True
                print(i, hex(self.registers[i]))
        if not any_updates:
            print("No updated values")
        print("\n")

    def _get_register(self, register_num): # useful for asic_grid level debugging?
        # returns a padded 8 byte register as a string
        val = self.registers[register_num]
        return hexify(val)
    
    def print_tx_buffers(self):
        print(self.tx_buffers)


class ASIC_GRID(io_request_iface): # config defined: should take in a yaml instead of software level
    # reasonable balance between "anything is allowed" and "specific setup", should have some physical constraints
    # should always be a rectangular-ish grid
    # specify input port for fpga

    # doesn't do anything right now
    # do i need this? should the ASIC directly slot into something already in larpix-lib?
    # no i should need it, the packets only come/go from one place
    # hmm but the hydra strand literally handles this, should i just init a bunch of asics and throw them into strand?
    # but it might be nice to have a network that can clock/update...? unsure what strand really does
    # will keep for now
    
    def __init__(self, hw_yaml, asic_spec):
        
        self.asic_spec = asic_spec
        self.asic_num_ports = asic_spec.num_ports()
        self._dirs = ["n", "w", "s", "e"] # match with 
        self.out_idx = asic_spec.output_indices(self._dirs) # [1, 2, 3, 0]
        self.in_idx = asic_spec.input_indices(self._dirs) # [0, 1, 2, 3]

        self.asic_ids = {} # dict from hardware id (not the same as asic's chip_id) to actual ASIC objects
        self.asic_connections = {} # dict from hardware id to dict of num_ports connected ids ({n,w,s,e} for 4?)
        # needs: root_asics (where the fpga sends packets to), could be multiple, needs connected direction as well
        # dict from fpga out to [asic, which dir asic is connected on]
        self.root_asics = {} # {fpga channel: [asic_id, direction asic receives on]}

        # for debugging: need some idea of grid geometry so it can draw the grid
        self.x_min = np.inf
        self.x_max = -np.inf
        self.y_min = np.inf
        self.y_max = -np.inf
        self.loc_dic = {} # loc to physical id
        
        # parse hw yaml!
        hw_cfg = common.dict_from_yaml(hw_yaml)
        
        # iterate over asics in grid
        for asic_dic in hw_cfg["asics"]:
            # checks for valid yaml
            if not ("physical_id" in asic_dic.keys() and "connections" in asic_dic.keys()):
                print("no id/connections in yaml, breaking")
                break
            
            # make an asic
            asic = ASIC(self.asic_spec)

            # set {asic_id:asic}
            asic_id = asic_dic["physical_id"]
            self.asic_ids[asic_id] = asic

            asic_loc = asic_dic["loc"]
            asic_x = asic_loc[0]
            asic_y = asic_loc[1]
            asic_loc_tuple = (asic_x, asic_y)
            self.loc_dic[asic_loc_tuple] = asic_id
            self.x_min = min(self.x_min, asic_x)
            self.x_max = max(self.x_max, asic_x)
            self.y_min = min(self.y_min, asic_y)
            self.y_max = max(self.y_max, asic_y)

            # set {asic_id: {dir: neighbor_id}}
            self.asic_connections[asic_id] = {}
            connections = asic_dic["connections"] # connections will be {dir: neighbor_id}
            for dir in connections.keys():
                neighbor_id = connections[dir]
                if isinstance(neighbor_id, str):
                    self.root_asics[neighbor_id] = [asic_id, dir] # e.g. root_asics["fpga0"] = [asic_id, receiving channel]
                self.asic_connections[asic_id][dir] = neighbor_id
            
        # TODO: check if nonexistent/one-way connections
        for asic_id in self.asic_ids.keys():
            pass

        
        # some way to time/sync/clock the network
        self.actions = 0
        self.init_time = time.time() # dunno if will need

        self.received_packets = [] 

        

    def send_packets_to_root(self, packets):
        for packet in packets:
            for fpga_channel in self.root_asics.keys(): # direction matters? right now packets always go out in same order
                asic_id = self.root_asics[fpga_channel][0]
                receiving_dir = self.root_asics[fpga_channel][1]
                asic = self.asic_ids[asic_id]
                self.send_packet_individual(asic, receiving_dir, packet)

    def send_packet_individual(self, asic, dir, packet):
        receive_chan = self.dir_to_idx(self.invert_dir(dir))
        asic.rx(packet, receive_chan)
    
    def update(self, cycles=1, timeout=1000000):
        if cycles < 0: # update until empty if negative arg given
            while not self.all_asic_buffers_empty(): # add a break condition
                self._single_update()
        else:
            for _ in range(cycles):
                if self.all_asic_buffers_empty():
                    break
                self._single_update()

    def _single_update(self):
        # pop one packet from each buffer
        for id in self.asic_ids.keys(): # iterate over asics
            asic = self.asic_ids[id]
            if asic.tx_all_empty(): # skip if asic empty
                continue
            connection_dic = self.asic_connections[id]
            for chan in range(len(self._dirs)): # iterate over asic's channels
                # check if buffer is empty
                if asic.tx_empty(chan):
                    continue
                else:
                    packet = asic.tx(chan)
                    out_dir = self.idx_to_dir(chan, asic_out=True)
                    receiver_id = connection_dic[out_dir]
                    if type(receiver_id) == int:
                        # send to asic
                        receiving_asic = self.asic_ids[receiver_id]
                        receive_dir = self.invert_dir(out_dir)
                        receive_chan = self.dir_to_idx(receive_dir)
                        receiving_asic.rx(packet, receive_chan)
                    elif type(receiver_id) == str:
                        # send to fpga
                        self.received_packets.append(hexify(packet)) #TODO: add print method later with hex so that here it can stay as ints
                    else:
                        print("exception in asic_grid.update()")

    def all_asic_buffers_empty(self):
        return all([asic.tx_all_empty() for asic in self.asic_ids.values()])

    def invert_dir(self, dir:str) -> str:
        idx = self._dirs.index(dir)
        return self._dirs[(idx + 2) % 4]

    def dir_to_idx(self, dir, asic_out:bool=False): # to send to asic
        i = self._dirs.index(dir)
        if asic_out:
            dirs = self.out_idx
        else:
            dirs = self.in_idx
        return dirs[i]

    def idx_to_dir(self, idx, asic_out:bool=True): # receiving from asic
        if asic_out:
            dirs = self.out_idx
        else:
            dirs = self.in_idx
        return self._dirs[dirs.index(idx)]
    
    # debugging tools
    def print_grid(self, keyword=None): # TODO: need to add where fpgas are connected later
        # default to printing physical id
        if keyword is not None and not (type(keyword) == str or type(keyword) == int):
            print("keyword type not supported")
            return
        if type(keyword) == int and (keyword < 0 or keyword > 255):
            print("printing register out of bounds")
            return
        if type(keyword) == str and keyword not in self.asic_spec.field_to_reg:
            print(f"{keyword} not in field_to_reg")
        else:
            for y in range(self.y_min, self.y_max+1):
                print("___________" * (self.x_max-self.x_min+1), end="\n")
                for x in range(self.x_min, self.x_max+1):
                    print("|", end="")
                    loc = (x,y)
                    if loc in self.loc_dic:
                        asic_id = self.loc_dic[loc]
                        if type(keyword) == str:
                            asic = self.asic_ids[asic_id]
                            val = asic._get_register(self.asic_spec.field_to_reg[keyword][0])
                            print(val, end="")
                        elif type(keyword) == int:
                            asic = self.asic_ids[asic_id]
                            val = asic._get_register(keyword)
                            print(val, end="")
                        else:
                            print(hexify(asic_id), end="")
                    else:
                        print(f"          ", end="")
                print("|",end="\n")
            print("___________" * (self.x_max-self.x_min+1), end="\n")



    # interface capabilities
    def send_packets(self, io_chan, packets):
        self.send_packets_to_root(packets)
        # needs to return messages from asics in network
        return # Returns a list of reply bytes (or None if timeout).
    
    def send_string(self, s): # should be a high level command, e.g. "reset_all" to reset all asics in grid
        pass
    
    def set_timeout(self, timeout_ms): # shrug, maybe to catch loops? grid needs to track timesteps/# actions taken
        pass