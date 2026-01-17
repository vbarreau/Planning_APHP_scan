from box import box 
from datetime import datetime

class event:
    def __init__(self, name: str, beg: str = '09:00', end: str = '09:45', box: box |None = None, flag: int = 1, day: str = '2025-01-01'):
        self.name = name
        self.day = day
        self.beg = ''.join(c for c in beg if c.isdigit() or c == ':')
        self.end = ''.join(c for c in end if c.isdigit() or c == ':')
        self.box = box if box is not None else box() # type: ignore
        self.flag = flag
        
    def __str__(self):
        return f"Event(name: {self.name}, day: {self.day}, beg: {self.beg}, end: {self.end}, flag: {self.flag})"
    
    def unpack(self):
        return self.box.unpack() + [self.name, self.flag] 
    
    def weekday(self):
        return datetime.strptime(self.day, '%Y-%m-%d').weekday()

    def getWeekdayFromTable(self, days_x, week):
        """
        Assigns week[i] to self.day only if the box is more than 50% inside days_x[i].

        Parameters:
        - days_x: list of tuples (x_min, x_max) representing day column boundaries
        - week: list of date strings corresponding to each day
        """
        box_left = self.box.x
        box_right = self.box.x + self.box.w
        box_width = self.box.w

        for i, (x_min, x_max) in enumerate(days_x):
            # Calculate the overlap between the box and this day's column
            overlap_left = max(box_left, x_min)
            overlap_right = min(box_right, x_max)
            overlap_width = max(0, overlap_right - overlap_left)

            # Check if more than 50% of the box is inside this day's column
            if overlap_width > 0.5 * box_width:
                self.day = week[i]
                break

