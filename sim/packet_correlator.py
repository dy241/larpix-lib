import copy
import larpix_control.asic.asic_spec as _as

class PacketCorrelator:
    def __init__(self, asic_spec: _as.asic_spec):
        # will it be useful to have a list of packets in/out?
        self.asic_spec = asic_spec
        self.reply_dic = {} # {(io_group, io_chan, chip_id, addr) : [n expected, [packet list]]}
        self.unmatched_packets_dic = {} # same format as reply_dic, holds unexpected reply packets

    def set_packets_in(self, pkt_list): # pkt list in format [(pkt, io_group, io_chan), ...]
        # resets everything
        self.reply_dic = {}
        self.unmatched_packets_dic = {}
        # parse pkt_list into key of dict
        for pkt_tuple in pkt_list:
            pkt = pkt_tuple[0]
            io_group = pkt_tuple[1]
            io_chan = pkt_tuple[2]
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
        # parse
        for pkt_tuple in pkt_list:
            pkt = pkt_tuple[0]
            io_group = pkt_tuple[1]
            io_chan = pkt_tuple[2]
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