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


    