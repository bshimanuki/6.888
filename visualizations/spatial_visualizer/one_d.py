# Super class to make draggable items
# To inherit, Subclass and create a shape.  Set self.id
# Als, define self.get_center()
class DraggablePoint(object):
    def __init__(self, canvas, coord, color, activecolor, tags="token"):
        self.canvas = canvas
        self.coord = coord
        self.color = color
        self.activecolor = activecolor
        self.tags = tags

        self.box = None
        self.text = None
        self.display = False

        # Register functions
        self.register_arrow_functions()

        self.id = None

        self.create_object()

    def create_object(self):
        pass

    def move_object(self, center_coords):
        self.coord = center_coords
        self.canvas.delete(self.id)
        self.create_object()
        if self.display:
            self.display_label(self.display)

    def get_id(self):
        return self.id

    def get_coords(self):
        return self.coord

    def get_center(self):
        (x, y, x2, y2) = self.canvas.coords(self.id)
        return ((x+x2)/2, (y+y2)/2)

    def on_token_press(self, event):
        '''Begining drag of an object'''
        self.coord = (event.x, event.y)

    def on_token_release(self, event):
        '''End drag of an object'''
        pass

    def on_token_motion(self, event):
        '''Handle dragging of an object'''
        # compute how much the mouse has moved
        (x, y) = self.coord
        delta_x = event.x - x
        delta_y = event.y - y
        # move the object the appropriate amount
        self.canvas.move(self.id, delta_x, delta_y) # The actual updating!!!
        # record the new position
        self.coord = (event.x, event.y)

        # Try to display a label, or delete one
        self.display_label(self.display)

    def register_arrow_functions(self):
        self.canvas.tag_bind(self.tags, "<ButtonPress-1>", self.on_token_press)
        self.canvas.tag_bind(self.tags, "<ButtonRelease-1>", self.on_token_release)
        self.canvas.tag_bind(self.tags, "<B1-Motion>", self.on_token_motion)

    def display_label(self, display):
        self.display = display
        if self.box != None:
            self.canvas.delete(self.box)
        if self.text != None:
            self.canvas.delete(self.text)

        if self.display:
            x, y = self.get_center()
            WIDTH = 20
            HEIGHT = 10
            OFFSET = 30
            color = "orange"
            self.box = self.canvas.create_rectangle(x-WIDTH-OFFSET, y-HEIGHT, x+WIDTH-OFFSET, y+HEIGHT,
                                    outline=color, fill=color, activefill="white", tags=self.tags)
            self.text = self.canvas.create_text(x - OFFSET, y, text=self.tags)# + str(self.id))


class DraggableOval(DraggablePoint):
    def create_object(self):
        (x,y) = self.coord
        SIZE = 10
        self.id = self.canvas.create_oval(x-SIZE, y-SIZE, x+SIZE, y+SIZE,
                        outline=self.color, fill=self.color,
                        activefill=self.activecolor, activeoutline="white", tags=self.tags)


class DraggableLine(DraggablePoint):
    def create_object(self):
        x, y = self.coord
        SIZE = 10
        coords = ((x-SIZE, y-SIZE), (x+SIZE, y+SIZE))
        self.id = self.canvas.create_line(coords, width=5.0, tags=self.tags)
        self.canvas.itemconfig(self.id, fill="blue") # change color


class DraggablePE(DraggablePoint):
    def create_object(self):
        x, y = self.coord
        SIZE = 15
        coords = ((x-SIZE, y-SIZE), (x+SIZE, y+SIZE))
        self.id = self.canvas.create_rectangle(coords, width=5.0, tags=self.tags)
        self.canvas.itemconfig(self.id, fill="blue") # change color

    def set_light(self, on):
        if on:
            self.canvas.itemconfig(self.id, fill="yellow") # change color
        else:
            self.canvas.itemconfig(self.id, fill="blue") # change color


class DraggableSRAM(DraggablePoint):
    def create_object(self):
        x, y = self.coord
        SIZE = 15
        coords = ((x-SIZE, y-SIZE), (x+SIZE, y+SIZE))
        self.id = self.canvas.create_rectangle(coords, width=5.0, tags=self.tags)
        self.canvas.itemconfig(self.id, fill="grey") # change color

    def set_light(self, cmd):
        if cmd == "read":
            self.canvas.itemconfig(self.id, fill="green") # change color
        elif cmd == "write":
            self.canvas.itemconfig(self.id, fill="red") # change color
        elif cmd == "clear":
            self.canvas.itemconfig(self.id, fill="grey") # change color
        elif cmd == "reverse":
            self.canvas.itemconfig(self.id, fill="purple") # change color
        else:
            print("invalid sram cmd recieved by ", self.id)
