from asic_classes import *

def hexify(num):
    # return a 8 byte padded hex string given an int
    # https://stackoverflow.com/questions/12638408/decorating-hex-function-to-pad-zeros
    return f"{num:#0{10}x}"


# for asic
def all_registers_reset_value(field_to_reg, field_to_reset_value, num_registers):
    reset_arr = [0x0] * num_registers
    for field in field_to_reg.keys():
        reg, width, offset, mask = field_to_reg[field]
        reset_value = field_to_reset_value[field] # keys dont match

        reg_val = reset_arr[reg]
        reset_value = reset_value * 2 ** offset

        reset_value = reset_value & mask
        reg_val = reg_val | reset_value
        reset_arr[reg] = reg_val
    return reset_arr

def get_enable_arr(asic, keyword):
    enables = [None] * asic.num_ports
    for idx in range(asic.num_ports):
        reg, width, offset, mask = asic.field_to_reg[f"{keyword}[{idx}]"]
        reg_val = asic.registers[reg]
        idx_val = (reg_val & mask) >> offset
        enables[idx] = idx_val
    return enables

def get_reg(asic, keyword):
    reg, width, offset, mask = asic.field_to_reg[f"{keyword}"]
    reg_val = asic.registers[reg]
    val = (reg_val & mask) >> offset
    return val

def set_register(asic, reg, width, offset, val):
    # TODO: check if bits or val exceed register size
    if reg >= asic.num_registers:
        print("register out of range")
        return
    if val >= 2 ** asic.reg_size:
        print("trying to set value larger than register size")
    reg_val = asic.registers[reg]
    val = val * 2 ** offset
    val = val % (2 ** asic.reg_size)
    mask = 2 ** (width + offset) - 2 ** offset # ones where bits should be replaced
    reg_val = reg_val & (~mask & (2 ** asic.reg_size - 1)) # TODO: replace with 2 ** regsize - 1
    reg_val = reg_val | val
    asic.registers[reg] = reg_val

def _add_packet_to_buffers(asic, packet):
    buffer_idxs = [0] * asic.num_ports # if not valid, dont add to any buffers
    if asic.asic_spec.valid_downstream_packet(packet):
        # send downstream
        buffer_idxs = asic._get_downstream_enables()
    elif asic.asic_spec.valid_upstream_packet(packet):
        # send upstream
        buffer_idxs = asic._get_upstream_enables()
    for i in range(asic.num_ports):
        if buffer_idxs[i]:
            asic.tx_buffers[i].append(packet)

def rx(asic: ASIC, packet:int, channel:int): 
    # TODO: document (and move to helper)
    # check if listening on channel
    if (channel >= 0) and (not asic._get_listen_enables()[channel]): # ignore listen check if channel is negative (for debugging)
        return
    
    chip, addr, val = asic.asic_spec.parse_chip_address_value(packet)
    if chip == asic._get_chip_id():
        if asic.asic_spec.valid_config_read_request(packet):
            response_val = asic.registers[addr]
            response_packet = asic.asic_spec.build_config_packet(chip, addr, response_val, downstream=1, write=False)
            _add_packet_to_buffers(asic, response_packet)
        elif asic.asic_spec.valid_config_read_response(packet):
            _add_packet_to_buffers(asic, packet)
        elif asic.asic_spec.valid_config_write(packet):
            set_register(asic, addr, 8, 0, val)
    else:
        # "not for me"
        _add_packet_to_buffers(asic, packet)


# for AsicGrid    