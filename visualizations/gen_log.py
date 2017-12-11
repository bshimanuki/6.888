import sys
sys.path.append('..')
from nnsim.simulator import run_tb
from ws_2d.tb import WSArchTB

ws_tb = WSArchTB()
run_tb(ws_tb, verbose=False, dump_stats=True)
