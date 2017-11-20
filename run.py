from nnsim.simulator import run_tb
from meta_tb import MetaArchTB, Conv, FC

if __name__ == "__main__":
    layers = [
        Conv(image_size=(4, 4),
             filter_size=(3, 3),
             in_chn=7,
             out_chn=15,
             ),
    ]

    tb = MetaArchTB(arr_x=8,
                    arr_y=4,
                    chn_per_word=4,
                    layers=layers,
                    )
    run_tb(tb, verbose=False)
