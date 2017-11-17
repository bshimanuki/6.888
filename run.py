from conv_ws.tb import WSArchTB


if __name__ == "__main__":
    from nnsim.simulator import run_tb
    ws_tb = WSArchTB()
    run_tb(ws_tb, verbose=False)

