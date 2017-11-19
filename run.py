from conv_ws.tb import WSArchTB
from fc_os.tb import OSArchTB


if __name__ == "__main__":
    from nnsim.simulator import run_tb
    # tb = WSArchTB()
    tb = OSArchTB()
    run_tb(tb, verbose=False)

