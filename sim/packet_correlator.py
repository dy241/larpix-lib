import copy
import larpix_control.asic.asic_spec as _as

class PacketCorrelator:
    def __init__(self, asic_spec: _as.asic_spec):
        self.io_group = 0 # change once figure out how to incorporate io_group, io_chan
        self.io_chan = 0
        self.asic_spec = asic_spec
        self.packets_in = []
        self.packets_out = []
        self.reply_dic = {} # {(io_group, io_chan, chip_id, addr) : [n expected, [packet list]]}
        self.unmatched_packets_dic = {} # same format as reply_dic, holds unexpected reply packets

    def set_packets_in(self, pkt_list): # how to incorporate io_group/io_chan info?
        io_group = self.io_group
        io_chan = self.io_chan
        # parse pkt_list into key of dict
        for pkt in pkt_list:
            # validate each pkt is a valid read request
            if not self.asic_spec.valid_config_read_request(pkt): # not valid
                continue # disregard packet
            else:
                chip, addr, val = self.asic_spec.parse_chip_address_value(pkt)
                key = (io_group, io_chan, chip, addr)
                if key in self.reply_dic:
                    current = self.reply_dic[key] # mutable object
                    current[0] += 1
                else:
                    self.reply_dic[key] = [1, []]

    def add_packets_out(self, pkt_list):
        io_group = self.io_group
        io_chan = self.io_chan
        # parse
        for pkt in pkt_list:
            # validate each packet is a read response
            if not self.asic_spec.valid_config_read_response(pkt):
                continue # disregard packet
            else:
                chip, addr, val = self.asic_spec.parse_chip_address_value(pkt)
                key = (io_group, io_chan, chip, addr)
                if key in self.reply_dic:
                    current = self.reply_dic[key] # mutable object
                    current[1].append(pkt)
                elif key in self.unmatched_packets_dic:
                    current = self.unmatched_packets_dic[key]
                    current[1].append(pkt)
                else:
                    self.unmatched_packets_dic[key] = [0, [pkt]]

    def done(self):
        return all([val[0] == len(val[1]) for val in self.reply_dic.values()])

    def reply(self):
        return copy.deepcopy(self.reply_dic)