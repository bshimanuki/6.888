import json
from re import search, match

# Trace format example:
# [ {"name": "Asub", "cat": "PERF", "ph": "B", "pid": 22630, "tid": 22630, "ts": 829},
#  {"name": "Asub", "cat": "PERF", "ph": "E", "pid": 22630, "tid": 22630, "ts": 833} ]
# ( Doc: https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview )

def cvt_log_to_trace(input_log_file):
    EARLY_CUTOFF = 10000

    f = open(input_file, 'r')
    trace = []
    tick = 0
    for i, line in enumerate(f):
        if i > EARLY_CUTOFF:
            break

        # print(line, end='')
        if " Tick " in line:
            newtick = int(line.split()[2][1:])
            assert(newtick == tick)
            tick += 1
        elif " NTick " in line:
            pass
        else:
            name = line.split()[0]
            if line.split()[0] == "chn":
                trace.append({"name": "my_chn", "cat": "chn", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": "my_chn", "cat": "chn", "ph": "E", "pid": hash(name), "ts":tick+1})
            elif line.split()[0] == "pe":
                trace.append({"name": "my_pe", "cat": "pe", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": "my_pe", "cat": "pe", "ph": "E", "pid": hash(name), "ts":tick+1})
            elif line.split()[0] == "sram":
                trace.append({"name": "my_sram", "cat": "sram", "ph": "B", "pid": hash(name), "ts":tick})
                trace.append({"name": "my_sram", "cat": "sram", "ph": "E", "pid": hash(name), "ts":tick+1})
            else:
                print("This line did not follow format: ", line)
                assert(False)

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

if __name__ == '__main__':
    input_file = '../wsarch_log.txt'
    output_file = 'trace.json'

    # Convert
    trace = cvt_log_to_trace(input_file)
    # for item in trace:
    #     item["ts"] /= 1000

    # Print and Write
    # print_trace(trace)
    dump_trace(output_file)
