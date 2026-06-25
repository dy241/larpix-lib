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



# for asic_grid    