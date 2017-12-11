import tkinter as tk
from PIL import ImageTk, Image
from re import search, match

from one_d import DraggablePE, DraggableSRAM
from two_d import ChannelArrow, DraggableBox
from log_parse import get_and_parse_log, assert_valid_log


class Base(tk.Frame):
    '''Illustrate how to drag items on a Tkinter canvas'''

    def __init__(self, parent, tick_list, chn_name_map, pe_name_map, sram_name_map, ntick, arr_x, arr_y):
        self.parent = parent
        tk.Frame.__init__(self, parent)
        self.tick_list = tick_list
        self.curr_tick = 0
        self.chn_name_map = chn_name_map
        self.pe_name_map = pe_name_map
        self.sram_name_map = sram_name_map
        self.ntick = ntick
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.configure(background='grey')

        # create a canvas
        self.img_sz = (650, 750)
        self.canvas = tk.Canvas(width=self.img_sz[0]+300, height=self.img_sz[1])
        self.canvas.pack(fill="both", expand=True)

        # Add GUI elements
        self.NUM_ARROWS = len(self.chn_name_map)
        self.NUM_PES = len(self.pe_name_map)
        self.NUM_SRAMS = 3
        self.label_state = False
        print("NUM_ARROWS={}, NUM_PES={}, NUM_SRAMS={}".format(
            self.NUM_ARROWS,
            self.NUM_PES,
            self.NUM_SRAMS)
        )

        self.arrow_coords = []
        self.arrows = []
        self.pe_coords = []
        self.pes = []
        self.sram_coords = []
        self.srams = []
        self.draggable_pe_box_coords = None

        self._load_positions(positions_file="SAVED_POSITIONS.txt")
        self._add_arrows()
        self._add_pes()
        self._add_dragable_pe_box()
        self._add_srams()
        self._add_play_buttons()
        self._add_save_button(positions_file="SAVED_POSITIONS.txt")
        self._add_label_checkboxes()
        self._add_background()

        # DEBUG
        self.count = 0

    def save_positions(self, positions_file):
        print("Saving positions")
        f = open(positions_file, 'w')
        for arrow in self.arrows:
            coords = arrow.get_line_coords()
            string = ",".join([str(num) for num in coords]) + "\n"
            print(string, end='')
            f.write(string)

        for pe in self.pes:
            coords = pe.get_center()
            string = ",".join([str(num) for num in coords]) + "\n"
            print(string, end='')
            f.write(string)

        for sram in self.srams:
            coords = sram.get_center()
            string = ",".join([str(num) for num in coords]) + "\n"
            print(string, end='')
            f.write(string)

        # Save dragable_pe_box Coords
        coords = self.dragable_pe_box.get_line_coords()
        string = ",".join([str(num) for num in coords]) + "\n"
        print(string, end='')
        f.write(string)

    def _load_positions(self, positions_file):
        print("Loading positions")
        f = open(positions_file, 'r')

        for i, line in enumerate(f):
            coords = [float(num) for num in line.split(',')]
            if i < self.NUM_ARROWS:
                self.arrow_coords.append(coords)
            elif i < self.NUM_ARROWS + self.NUM_PES:
                self.pe_coords.append(coords)
            elif i < self.NUM_ARROWS + self.NUM_PES + self.NUM_SRAMS:
                self.sram_coords.append(coords)
            else:
                self.draggable_pe_box_coords = coords


    def _add_arrows(self):
        self.arrows = []
        arrow_names = list(self.chn_name_map.keys())
        for i in range(self.NUM_ARROWS):
            if i < len(self.arrow_coords):
                x, y, x2, y2 = self.arrow_coords[i]
            else:
                x = 100 + 2*i
                y = 100 + 2*i
                x2 = 100 + 2*i
                y2 = 140 + 2*i
            tags = arrow_names[i]
            arrow = ChannelArrow(self.canvas, (x, y, x2, y2), "white", tags=tags)
            self.arrows.append(arrow)

    def _add_dragable_pe_box(self):
        if self.draggable_pe_box_coords == None:
            x, y, x2, y2 = 320, 100, 800, 380
        else:
            x, y, x2, y2 = self.draggable_pe_box_coords
        self.dragable_pe_box = DraggableBox(self.canvas, (x, y, x2, y2), "white",
                                    pes=self.pes, chns=self.arrows,
                                    arr_x=self.arr_x, arr_y=self.arr_y,
                                    chn_name_map = self.chn_name_map,
                                    pe_name_map = self.pe_name_map,
                                    sram_name_map = self.sram_name_map,
                                    tags="dragable_pe_box")

    def _add_pes(self):
        self.pes = []
        pe_names = list(self.pe_name_map.keys())
        for i in range(self.NUM_PES):
            if i < len(self.pe_coords):
                coords = self.pe_coords[i]
            else:
                coords = ((150 + 20*i, 200))
            tags = pe_names[i]
            self.pes.append(DraggablePE(self.canvas, coords, "blue", "", tags=tags))

    def _add_srams(self):
        self.srams = []
        sram_names = list(self.sram_name_map.keys())
        for i in range(self.NUM_SRAMS):
            if i < len(self.sram_coords):
                coords = self.sram_coords[i]
            else:
                coords = ((150 + 20*i, 300))
            tags = sram_names[i]
            self.srams.append(DraggableSRAM(self.canvas, coords, "grey", "", tags=tags))

    def _add_play_buttons(self):
        def dec_tick():
            for pe in self.pes:
                pe.set_light(False)

            for sram in self.srams:
                sram.set_light("clear")

            for arrow in self.arrows:
                arrow.draw_extras() # Redraw

            if self.curr_tick == 0: # Tick >= 0
                return
            self.curr_tick -= 1
            print()
            for i in range(len(self.tick_list[self.curr_tick])):
                self.update(self.tick_list[self.curr_tick][i], reverse=True)
            print("tick: ", self.curr_tick)

        b = tk.Button(text="Dec tick", command=dec_tick)
        b.place(relx=0.75, rely=0.65, anchor=tk.CENTER, height=100, width=100)

        def inc_tick():
            for pe in self.pes:
                pe.set_light(False)

            for sram in self.srams:
                sram.set_light("clear")

            for arrow in self.arrows:
                arrow.draw_extras() # Redraw

            for i in range(len(self.tick_list[self.curr_tick])):
                self.update(self.tick_list[self.curr_tick][i])
            self.curr_tick += 1
            if self.curr_tick > self.ntick:
                print("At end of log!")
                self.curr_tick = self.ntick
            print("tick: ", self.curr_tick)

        b = tk.Button(text="Inc tick", command=inc_tick)
        b.place(relx=0.90, rely=0.65, anchor=tk.CENTER, height=100, width=100)

        self.parent.bind('<Left>', lambda x: dec_tick())
        self.parent.bind('<Right>', lambda x: inc_tick())

    def _add_save_button(self, positions_file):
        b = tk.Button(text="Save positions", command=lambda: self.save_positions(positions_file))
        b.place(relx=0.75, rely=0.85, anchor=tk.CENTER, height=100, width=100)

        self.parent.bind('s', lambda x: save_positions())

    def _add_label_checkboxes(self):
        self.display_labels = tk.IntVar()
        def checkbox_func():
            # self.display_labels = not self.display_labels
            print("self.display_labels = ", self.display_labels.get())
        b = tk.Checkbutton(text="Display Labels", command=checkbox_func,
            variable=self.display_labels, padx=15)
        b.place(relx=0.9, rely=0.85, anchor=tk.CENTER, height=100, width=100)

        self.parent.bind('s', lambda x: save_positions())

    def _add_background(self):
        img_path = "ws_arch.jpg"

        # Creates a Tkinter-compatible photo image, which can be
        # used everywhere Tkinter expects an image object.
        pil_img = Image.open(img_path)
        pil_img = pil_img.resize(self.img_sz, Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(pil_img)

        width, height = self.img_sz
        self.actual_img = self.canvas.create_image(width/2, height/2, image = self.img)
        self.canvas.lower(self.actual_img)

    # Entry point for handling ALL individual updates
    # Currently supports:
    #   1) chn # push/pop
    #   2) pe # fire
    def update(self, line, reverse=False):
        print("update: ", line, end='')
        # Chn# push/pop
        if search("chn", line) != None:
            _, chn_name, cmd = line.split()
            assert(chn_name in chn_name_map.keys())
            chn_num = chn_name_map[chn_name]
            assert(cmd in ["push", "pop"])
            assert(0 <= chn_num and chn_num < self.NUM_ARROWS)
            arrow = self.arrows[chn_num]
            if (cmd == "pop" and not reverse) or (cmd =="push" and reverse):
                arrow.dec_count()
            else:
                arrow.inc_count()
        elif search("pe", line) != None:
            # PE Fired
            _, pe_name, cmd = line.split()
            assert(pe_name in pe_name_map.keys())
            pe_num = pe_name_map[pe_name]
            assert(cmd == "fire")
            assert(0 <= pe_num and pe_num < self.NUM_PES), "pe_num={}, self.NUM_PES={}".format(pe_num, self.NUM_PES)
            assert(0 <= pe_num and pe_num < self.NUM_PES)
            assert(self.NUM_PES == len(self.pes))
            self.pes[pe_num].set_light(True)

        elif search("sram", line) != None:
            # PE Fired
            _, sram_name, cmd = line.split()
            assert(sram_name in sram_name_map.keys())
            sram_num = sram_name_map[sram_name]
            assert(cmd in ["read", "write", "clear"])
            assert(0 <= sram_num and sram_num < self.NUM_SRAMS)
            self.srams[sram_num].set_light(cmd)


    def tick(self):
        if self.display_labels.get() != self.label_state:
            print("toggling labels")
            for arrow in self.arrows:
                arrow.display_label(self.display_labels.get())
            for pe in self.pes:
                pe.display_label(self.display_labels.get())
            for sram in self.srams:
                sram.display_label(self.display_labels.get())
            self.label_state = self.display_labels.get()

        self.canvas.after(400, self.tick) # To make the thing infinitely repeat!


if __name__ == "__main__":
    file_path = 'LOG.txt'

    # Make sure log format is valid
    assert_valid_log(file_path)
    tick_list, chn_name_map, pe_name_map, sram_name_map, ntick = \
        get_and_parse_log(file_path)

    root = tk.Tk()
    base = Base(root, tick_list, chn_name_map, pe_name_map, sram_name_map, ntick, 8, 4)
    print("tick 0")
    base.tick()
    root.mainloop()
