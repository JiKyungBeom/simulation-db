from tod import TodInputModule
if __name__ == '__main__':
    tlLogic_name = ['1.Sindong396-7']
    k_0 = [0, 0, 0, 0]
    k_1 = [0, 0, 0, 0]
    k_2 = [0, 0, 0, 0]
    k_cen = [k_0] + [k_1] + [k_2]
    tod_input_module = TodInputModule(len(tlLogic_name), tlLogic_name, k_0, k_1, k_2, k_cen)
    data = tod_input_module.create_tod_table()
    print(data)