import json
from re import search, match

# Trace format example:
# [ {"name": "Asub", "cat": "PERF", "ph": "B", "pid": 22630, "tid": 22630, "ts": 829},
#  {"name": "Asub", "cat": "PERF", "ph": "E", "pid": 22630, "tid": 22630, "ts": 833} ]
# ( Doc: https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview )

def cvt_log_to_trace(input_log_file):
    # EARLY_CUTOFF = 10000

    f = open(input_file, 'r')
    trace = []
    tick = 0
    mode = "NA"
    for i, line in enumerate(f):
        # if i > EARLY_CUTOFF:
        #     break

        # print(line, end='')
        if " Tick " in line:
            newtick = int(line.split()[2][1:])
            assert(newtick == tick)
            tick += 1
        elif " NTick " in line:
            pass
        elif "CONV MODE" in line:
            if mode in ["CONV", "FC"]:
                trace.append({"name": mode, "cat": "layer_chg", "ph": "E", "pid": 0, "tid": hash(mode), "ts":tick})
            mode = "CONV"
            trace.append({"name": "CONV", "cat": "layer_chg", "ph": "B", "pid": 0, "tid": hash("CONV"), "ts":tick})
        elif "FC MODE" in line:
            if mode in ["CONV", "FC"]:
                trace.append({"name": mode, "cat": "layer_chg", "ph": "E", "pid": 0, "tid": hash(mode), "ts":tick})
            mode = "FC"
            trace.append({"name": "FC", "cat": "layer_chg", "ph": "B", "pid": 0, "tid": hash("FC"), "ts":tick})
        else:
            name = line.split()[0]
            if line.split()[0] == "chn":
                chn_name = line.split()[1]
                trace.append({"name": chn_name, "cat": "chn", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": chn_name, "cat": "chn", "ph": "E", "pid": hash(name), "ts":tick+1})
            elif line.split()[0] == "pe":
                trace.append({"name": "my_pe", "cat": "pe", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": "my_pe", "cat": "pe", "ph": "E", "pid": hash(name), "ts":tick+1})
            elif line.split()[0] == "sram":
                sram_name = line.split()[1]
                trace.append({"name": sram_name, "cat": "sram", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": sram_name, "cat": "sram", "ph": "E", "pid": hash(name), "ts":tick+1})
            else:
                print("This line did not follow format: ", line)
                assert(False)

    if mode in ["CONV", "FC"]:
        trace.append({"name": mode, "cat": "layer_chg", "ph": "E", "pid": 0, "tid": hash(mode), "ts":tick})

    return trace

def dump_trace(output_file):
    f = open(output_file, 'w')
    f.write('[')
    for item in trace[:-1]:
        f.write(str(item).replace('\'', '\"'))
        f.write(',\n')
    f.write(str(trace[-1]).replace('\'', '\"'))
    f.write(']\n')

def print_trace(trace):
    print('[', end='')
    for item in trace[:-1]:
        print(str(item).replace('\'', '\"'), end='')
        print(',')
    print(str(trace[-1]).replace('\'', '\"'), end='')
    print(']')

import sys
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Provide the log file to parse as an argument.")
        print("Ex: python cvt_to_trace.py ../../log.txt.")
        exit()

    input_file = sys.argv[1]
    # input_file = '../../log.txt'
    output_file = 'trace.json'

    # Convert
    trace = cvt_log_to_trace(input_file)
    # for item in trace:
    #     item["ts"] /= 1000

    # Print and Write
    # print_trace(trace)
    dump_trace(output_file)
