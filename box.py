import numpy as np

class box : 
    def __init__(self, x=0,y=0,w=100,h=30):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def unpack(self):
        return [self.x,self.y,self.w,self.h]

    def to_draw(self):
        return np.array([self.x,self.y,self.w,self.h])

    def __str__(self):
        return "x: " + str(self.x) + " y: " + str(self.y) + " w: " + str(self.w) + " h: " + str(self.h)

