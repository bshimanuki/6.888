from one_d import DraggableOval


class Arrow(object):
    def __init__(self, canvas, coords, color, tags):
        self.canvas = canvas
        self.line_side = None
        self.tags = tags

        self.box = None
        self.text = None
        self.display = False

        # Create two endpoints
        (x, y, x2, y2) = coords
        self.token_names = [self.tags + "a", self.tags + "b"]
        self.oval1 = DraggableOval(self.canvas, (x, y), "", "grey", tags=self.tags + "a")
        self.oval2 = DraggableOval(self.canvas, (x2, y2), "", "grey", tags=self.tags + "b")

        self.id_to_oval = {
            self.oval1.get_id(): self.oval1,
            self.oval2.get_id(): self.oval2,
        }

        # Create line
        x, y = self.oval1.get_center()
        x2, y2 = self.oval2.get_center()
        self.line_coords = ([x, y, x2, y2])
        self.line = self.canvas.create_line(self.line_coords, width=5.0, arrow="last")
        self.canvas.itemconfig(self.line, fill="blue") # change color
        self.canvas.lower(self.line)

        # Register functions
        self.register_arrow_functions()

    def move_line(self, new_coords):
        x, y, x2, y2 = new_coords
        self.oval1.move_object((x, y))
        self.oval2.move_object((x2, y2))
        self.on_token_motion(None)
        self.draw_extras()

    def on_token_press(self, event):
        '''Begining drag of an object'''
        # record the item and its location
        curr_id = self.canvas.find_closest(event.x, event.y)[0]
        self.line_side = (1 if curr_id == self.oval1.get_id() else 0)

    def on_token_release(self, event):
        '''End drag of an object'''
        assert(self.line_side != None)
        self.line_side = None

    def draw_extras(self):
        pass

    def on_token_motion(self, event):
        '''Handle dragging of an object'''
        # Update the line position
        (x, y) = self.oval1.get_center()
        (x2, y2) = self.oval2.get_center()
        self.line_coords = ([x, y, x2, y2])
        self.canvas.coords(self.line, self.line_coords)

        # Hook for metadata
        self.draw_extras()

        # Try to display a label, or delete one
        self.display_label(self.display)

    def on_token_motion_line(self, event):
        '''Handle dragging of an object'''
        # compute how much the mouse has moved
        print("on_token_motion_line")
        # for token_name in self.token_names:
        self.oval1.on_token_motion(event)
        self.oval2.on_token_motion(event)

    def register_arrow_functions(self):
        for token_name in self.token_names:
            self.canvas.tag_bind(token_name, "<ButtonPress-1>", self.on_token_press, add="+")
            self.canvas.tag_bind(token_name, "<ButtonRelease-1>", self.on_token_release, add="+")
            self.canvas.tag_bind(token_name, "<B1-Motion>", self.on_token_motion, add="+")

        # self.canvas.tag_bind("line", "<B1-Motion>", self.on_token_motion_line, add="+")

    def get_center(self):
        x, y = self.oval1.get_center()
        x2, y2 = self.oval2.get_center()
        return ((x + x2)/2, (y + y2)/2)

    def get_line_coords(self):
        return self.line_coords

    def display_label(self, display):
        self.display = display
        if self.box != None:
            self.canvas.delete(self.box)
        if self.text != None:
            self.canvas.delete(self.text)

        if self.display:
            x, y = self.get_center()
            WIDTH = 50
            HEIGHT = 10
            OFFSET = 30
            color = "orange"
            self.box = self.canvas.create_rectangle(x-WIDTH-OFFSET, y-HEIGHT, x+WIDTH-OFFSET, y+HEIGHT,
                                    outline=color, fill=color, activefill="white", tags=self.tags)
            self.text = self.canvas.create_text(x - OFFSET, y, text=self.tags)# + str(self.id))


class DraggableBox(Arrow):
    def __init__(self, canvas, coords, color, pes, chns, arr_x, arr_y, chn_name_map, pe_name_map, sram_name_map, tags="token"):
        super().__init__(canvas, coords, color, tags)
        # Add Rectangle element
        self.rect = self.canvas.create_rectangle(self.line_coords, width=5.0, tags=tags)
        self.canvas.itemconfig(self.rect, fill="grey")
        # Arrow should be below the box
        self.canvas.lower(self.rect)
        self.canvas.lower(self.line)
        self.pes = pes
        self.chns = chns
        self.arr_x = arr_x
        self.arr_y = arr_y

        self.chn_name_map = chn_name_map
        self.pe_name_map = pe_name_map
        self.sram_name_map = sram_name_map

        # Populate the box with pe's!
        self.sorted_pe_names = sorted(self.pe_name_map.keys())
        self.sorted_chn_names = sorted(self.chn_name_map.keys())
        self._draw_all_pes()

    def on_token_motion(self, event):
        super().on_token_motion(event)
        # Redraw the pes everytime the draggable box is manipulated
        self._draw_all_pes()


    def _draw_all_pes(self):
        self.canvas.coords(self.rect, self.line_coords)
        (x, y) = self.oval1.get_center()
        (x2, y2) = self.oval2.get_center()
        X_PADDING_RATIO = 0.1
        Y_PADDING_RATIO = 0.2
        x = x + (x2 - x) * X_PADDING_RATIO
        x2 = x2 - (x2 - x) * X_PADDING_RATIO
        y = y + (y2 - y) * Y_PADDING_RATIO
        y2 = y2 - (y2 - y) * Y_PADDING_RATIO
        assert(self.arr_x * self.arr_y == len(self.pes))

        for i in range(len(self.pes)):
            pe_name = self.sorted_pe_names[i]
            pe_idx = self.pe_name_map[pe_name]
            pe = self.pes[pe_idx]
            r = i // self.arr_x
            c = i % self.arr_x
            coords = ((x + (x2 - x)*(c / (self.arr_x - 1))),
                      (y + (y2 - y)*(r / (self.arr_y - 1))))
            pe.move_object(coords)

            # Will go through chn map and attach all the channels relevant
            # to each PE
            for i in range(len(self.chns)):
                chn_name = self.sorted_chn_names[i]

                # We have a match!
                if chn_name.split("_")[-2:] == pe_name.split("_")[-2:]:
                    chn_idx = self.chn_name_map[chn_name]
                    chn = self.chns[chn_idx]
                    pe_x, pe_y = pe.get_center()
                    if "filter" in chn_name:
                        chn.move_line([pe_x-30, pe_y, pe_x-15, pe_y])
                        chn.set_color("green")
                    elif "ifmap" in chn_name:
                        chn.move_line([pe_x-10, pe_y-30, pe_x-10, pe_y-15])
                        chn.set_color("blue")
                    elif "psum" in chn_name:
                        chn.move_line([pe_x+10, pe_y-30, pe_x+10, pe_y-15])
                        chn.set_color("red")
                    else:
                        assert(False), "Error in matching chns to pe_array!"



import math

class ChannelArrow(Arrow):
    def __init__(self, canvas, coords, color, tags="token"):
        super().__init__(canvas, coords, color, tags)

        self.ids = []
        self.count = 0

        # Draw the meta data initialy
        self.draw_extras()

    def set_color(self, color):
        self.canvas.itemconfig(self.line, fill=color)

    def set_count(self, count):
        self.count = count

    def dec_count(self):
        self.count -= 1

    def inc_count(self):
        self.count += 1

    def draw_dots(self, line_coords):
        SIZE=5
        color="red"

        for id in self.ids:
            self.canvas.delete(id)

        self.ids = []
        for i in range(self.count):
            x, y, x2, y2 = line_coords
            offset = 20 + 10 * i
            theta = math.atan2(y2 - y, x2 - x)
            x = x2 - offset * math.cos(theta)
            y = y2 - offset * math.sin(theta)
            id = self.canvas.create_oval(x-SIZE, y-SIZE, x+SIZE, y+SIZE,
                    outline=color, fill=color, activefill="white", tags=self.tags)
            self.ids.append(id)

    def draw_counter(self, line_coords):
        # Clear current metadata
        for id in self.ids:
            self.canvas.delete(id)

        def calc_center(coords):
            x, y, x2, y2 = coords
            return ((x+x2)/2, (y+y2)/2)
        x, y = calc_center(line_coords)
        SIZE = 10
        color = "orange"
        box = self.canvas.create_rectangle(x-SIZE, y-SIZE, x+SIZE, y+SIZE,
                    outline=color, fill=color, activefill="white", tags=self.tags)
        text = self.canvas.create_text(x - 5, y, text=str(self.count))

        SIZE = 4
        color = "red"
        offset = 5
        oval = self.canvas.create_oval(x-SIZE + offset, y-SIZE, x+SIZE + offset, y+SIZE,
                    outline=color, fill=color, activefill="white", tags=self.tags)

        # Record metadata
        self.ids = [box, text, oval]


    def draw_extras(self):
        if self.count < 3:
            self.draw_dots(self.line_coords)
        else:
            self.draw_counter(self.line_coords)
