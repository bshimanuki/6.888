This directory contains the spatial visualizer and temporal visualizer for 6888 nnsim.
Both are described in much mroe detail in our final paper submission.

The entry point for the spatial visualizer is gui.py.
To see ws_2d visualized:
cd 6.888/visualizations/
rm log.txt
python ws_2d_log_gen.py
python gui.py ../log.py ws_2d_pos.txt

To see meta_tb visualized:
cd 6.888/
rm log.txt
python run.py
python gui.py ../../log.py meta_tb_pos.txt
