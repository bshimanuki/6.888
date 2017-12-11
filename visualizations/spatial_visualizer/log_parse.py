from re import search, match

def get_and_parse_log(file_path):
    f = open(file_path, 'r')
    tick_list = [[]]
    tick = -1
    chn_name_map = {}
    pe_name_map = {}
    sram_name_map = {}
    for line in f:
        if search("NTick", line) != None:
            continue
        if search(" Tick", line) != None:
            new_tick = int(line.split()[2][1:])
            assert(new_tick == tick + 1)
            tick = new_tick
            tick_list.append([])
        else:
            tick_list[int(tick)].append(line)
            if search("chn", line) != None:
                chn_name = line.split()[1]
                if chn_name not in chn_name_map.keys():
                    chn_name_map[chn_name] = len(chn_name_map)
            elif search("pe", line) != None:
                pe_name = line.split()[1]
                if pe_name not in pe_name_map.keys():
                    pe_name_map[pe_name] = len(pe_name_map)
            elif search("sram", line) != None:
                sram_name = line.split()[1]
                if sram_name not in sram_name_map.keys():
                    sram_name_map[sram_name] = len(sram_name_map)
            else:
                print("offsensive line: ", line)
                assert(False)

    # print("tick = ", type(tick))
    # print("chn_name_map: ", chn_name_map)
    # print("pe_name_map: ", pe_name_map)
    # print("sram_name_map: ", sram_name_map)
    return tick_list, chn_name_map, pe_name_map, sram_name_map, tick


FORMAT = {
    "chn": "^chn \w+ (pop|push)$",
    "pe": "^pe \w+ fire$",
    "sram": "^sram \w+ (read|write)$",
}

def assert_valid_log(file_path):
    f = open(file_path, 'r')
    curr_tick = 0
    for line in f:
        if search("NTick", line) != None:
            pass
        elif search(" Tick", line) != None:
            tick = int(line.split()[2][1:])
            assert(curr_tick == tick)
            curr_tick += 1
        else:
            if search("chn", line) != None:
                if match(FORMAT["chn"], line) == None:
                    print(line)
                    assert(False)
            elif search("pe", line) != None:
                if match(FORMAT["pe"], line) == None:
                    print(line)
                    assert(False)
            elif search("sram", line) != None:
                if match(FORMAT["sram"], line) == None:
                    print(line)
                    assert(False)
            else:
                print("offsensive line: ", line)
                assert(False)
