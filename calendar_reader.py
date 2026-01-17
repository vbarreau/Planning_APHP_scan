"""
CalendarReader class for reading and parsing calendar PDFs/images.
"""

import re
import numpy as np
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import pytesseract

from event import event
from box import box


MONTHS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]


class CalendarReader:
    """
    Reads and parses calendar data from PDF or image files.
    Extracts events with their times and dates.
    """

    def __init__(self, file_path: str):
        """
        Initialize CalendarReader with a file path.

        Parameters:
        - file_path: Path to the PDF or image file
        """
        self.file_path = file_path
        self.image = None
        self.ocr_data = None
        self.lines = None
        self.columns = None
        self.events = None

    def load_image(self, dpi: int = 300) -> Image.Image:
        """
        Converts a PDF page to a high-resolution image or loads an image file.

        Parameters:
        - dpi: Resolution for PDF conversion

        Returns:
        - PIL Image object
        """
        ext = self.file_path[-3:].lower()

        if ext in ("png", "jpg"):
            self.image = Image.open(self.file_path)
        elif ext == "pdf":
            doc = fitz.open(self.file_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            size = [pix.width, pix.height]
            self.image = Image.frombytes("RGB", size, pix.samples)
        else:
            raise FileNotFoundError("File format not supported")

        return self.image

    def extract_text(self) -> dict:
        """
        Extract text from image with pytesseract.

        Returns:
        - Dict with keys: left, top, width, height, text (only non-empty entries)
        """
        if self.image is None:
            self.load_image()

        ocr_results = pytesseract.image_to_data(
            self.image, lang="eng", output_type=pytesseract.Output.DICT
        )

        # Filter to only non-empty text entries
        valid_indices = [i for i, t in enumerate(ocr_results["text"]) if t.strip()]

        self.ocr_data = {
            "left": [int(ocr_results["left"][i]) for i in valid_indices],
            "top": [int(ocr_results["top"][i]) for i in valid_indices],
            "width": [int(ocr_results["width"][i]) for i in valid_indices],
            "height": [int(ocr_results["height"][i]) for i in valid_indices],
            "text": [ocr_results["text"][i] for i in valid_indices]
        }

        return self.ocr_data

    def get_separators(self) -> tuple:
        """
        Identifies the horizontal and vertical separators in the image.

        Returns:
        - Tuple of (lines, columns) arrays
        """
        if self.image is None:
            self.load_image()

        img_array = np.array(self.image.convert("L"))
        img_array = 255 - img_array  # Invert colors

        vertical_sum = np.sum(img_array, axis=0)
        horizontal_sum = np.sum(img_array, axis=1)

        critere_line = 255 * self.image.width / 2
        critere_col = 255 * self.image.height / 3

        self.columns = np.where(vertical_sum > critere_col)[0]
        self.lines = np.where(horizontal_sum > critere_line)[0]

        return self.lines, self.columns

    @staticmethod
    def _within_columns(x1: int, x2: int, columns) -> bool:
        """Check whether a text is in a column (True) or across several (False)."""
        if columns is None:
            return True
        for col in columns:
            if x1 <= col <= x2 or x2 <= col <= x1:
                return False
        return True

    @staticmethod
    def _combine_box(data: dict, i1: int, i2: int) -> tuple:
        """Combines two boxes from ocr_data dict and returns a tuple of the combined values."""
        x1, y1, w1, h1 = data["left"][i1], data["top"][i1], data["width"][i1], data["height"][i1]
        x2, y2, w2, h2 = data["left"][i2], data["top"][i2], data["width"][i2], data["height"][i2]
        text1, text2 = data["text"][i1], data["text"][i2]

        return (
            min(x1, x2),
            min(y1, y2),
            max(x1 + w1, x2 + w2) - min(x1, x2),
            max(y1 + h1, y2 + h2) - min(y1, y2),
            text1 + " " + text2
        )

    def _group_lines(self, data: dict, x_threshold: int = 300, y_threshold: int = 50) -> dict:
        """
        Cleans the data by combining text boxes that are close enough to form a single sentence.
        Text is read from left to right, top to bottom.

        Parameters:
        - data: dict with keys left, top, width, height, text
        - x_threshold: maximum horizontal distance between boxes to be combined
        - y_threshold: maximum vertical distance between boxes to be combined

        Returns:
        - Cleaned data dict with same structure
        """
        n = len(data["text"])
        combined = True

        while combined:
            combined = False
            results = []
            i = n - 1
            while i > 0:
                x1, y1, w1 = data["left"][i - 1], data["top"][i - 1], data["width"][i - 1]
                x2, y2 = data["left"][i], data["top"][i]
                if (abs(x2 - (x1 + w1)) < x_threshold and
                    abs(y2 - y1) < y_threshold and
                    self._within_columns(x1, x2, self.columns) and
                    self._within_columns(y1, y2, self.lines)):
                    results.append(self._combine_box(data, i - 1, i))
                    i -= 2
                    combined = True
                else:
                    results.append((data["left"][i], data["top"][i], data["width"][i], data["height"][i], data["text"][i]))
                    i -= 1
            if i == 0:
                results.append((data["left"][0], data["top"][0], data["width"][0], data["height"][0], data["text"][0]))

            results.reverse()
            data = {
                "left": [r[0] for r in results],
                "top": [r[1] for r in results],
                "width": [r[2] for r in results],
                "height": [r[3] for r in results],
                "text": [r[4] for r in results]
            }
            n = len(data["text"])

        return data

    def _group_boxes(self, data: dict, x_threshold: int = 150, y_threshold: int = 75) -> dict:
        """
        Cleans the OCR data by combining text boxes that are close enough to form a single text area.

        Parameters:
        - data: dict with keys left, top, width, height, text
        - x_threshold: maximum horizontal distance between boxes to be combined
        - y_threshold: maximum vertical distance between boxes to be combined

        Returns:
        - Cleaned data dict with same structure
        """
        n = len(data["text"])
        combined_indices = set()
        results = []

        for i in range(n):
            if i in combined_indices:
                continue
            x1, y1, w1, h1 = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            text_parts = [data["text"][i]]
            combined_x1, combined_y1 = x1, y1
            combined_x2, combined_y2 = x1 + w1, y1 + h1

            for j in range(i + 1, n):
                if j in combined_indices:
                    continue
                x2, y2, w2, h2 = data["left"][j], data["top"][j], data["width"][j], data["height"][j]
                if (abs(x2 - x1) < x_threshold and
                    abs(y2 - y1) < y_threshold and
                    self._within_columns(x1, x2, self.columns) and
                    self._within_columns(y1, y2, self.lines)):
                    text_parts.append(data["text"][j])
                    combined_x1 = min(combined_x1, x2)
                    combined_y1 = min(combined_y1, y2)
                    combined_x2 = max(combined_x2, x2 + w2)
                    combined_y2 = max(combined_y2, y2 + h2)
                    combined_indices.add(j)

            results.append((
                combined_x1,
                combined_y1,
                combined_x2 - combined_x1,
                combined_y2 - combined_y1,
                " ".join(text_parts)
            ))

        return {
            "left": [r[0] for r in results],
            "top": [r[1] for r in results],
            "width": [r[2] for r in results],
            "height": [r[3] for r in results],
            "text": [r[4] for r in results]
        }

    def process(self) -> dict:
        """
        Full processing pipeline: load image, extract text, group text boxes.

        Returns:
        - Processed OCR data dict
        """
        self.load_image()
        self.extract_text()
        self.get_separators()

        # Regroup sentences
        data = self._group_lines(self.ocr_data, x_threshold=300, y_threshold=50)
        # Regroup logical boxes
        data = self._group_boxes(data, y_threshold=75)

        self.ocr_data = data
        return data

    @staticmethod
    def _get_days_indices(strings: list) -> list:
        """
        Returns the indices of the French date strings in a list of strings.
        """
        date_pattern = re.compile(
            r'\b\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b',
            re.IGNORECASE
        )
        indices = [i for i, s in enumerate(strings) if date_pattern.search(s) and "Le" not in s]
        indices.sort(key=lambda i: strings[i])
        return indices

    @staticmethod
    def _compact_string_day(s: str) -> str:
        """
        Converts a date from "weekday num month" (french) to datetime format (2026).
        """
        parts = s.split(sep=' ')
        num = int(parts[1])
        month_num = MONTHS.index(parts[2]) + 1
        return f"2026-{month_num:02d}-{num:02d}"

    def _get_weeks(self, data: dict) -> tuple:
        """
        From processed data, returns the weeks of the planning.

        Parameters:
        - data: dict with keys left, top, width, height, text

        Returns:
        - Tuple of (week dates list, day x-boundaries list)
        """
        days_i = self._get_days_indices(data["text"])
        days_i_sorted = np.zeros(len(days_i), dtype=int)

        for i in days_i:
            text_lower = data["text"][i].lower()
            if "lundi" in text_lower:
                days_i_sorted[0] = i
            elif "mardi" in text_lower:
                days_i_sorted[1] = i
            elif "mercredi" in text_lower:
                days_i_sorted[2] = i
            elif "jeudi" in text_lower:
                days_i_sorted[3] = i
            elif "vendredi" in text_lower:
                days_i_sorted[4] = i

        day_x_positions = [data["left"][i] for i in days_i_sorted]
        lines_sorted = np.sort(self.columns)

        days_x = []
        for day_x in day_x_positions:
            lines_before = lines_sorted[lines_sorted <= day_x]
            lines_after = lines_sorted[lines_sorted > day_x]

            x_min = lines_before[-1] if len(lines_before) > 0 else 0
            x_max = lines_after[0] if len(lines_after) > 0 else float('inf')

            days_x.append((x_min, x_max))

        week = []
        try:
            for i in range(5):
                week.append(self._compact_string_day(data["text"][days_i_sorted[i]]))
        except:
            print("Impossible de lire le planning. Si le fichier d'entrée est une photo, considérez utiliser une capture d'écran.")

        return week, days_x

    @staticmethod
    def _interpret_event_name(e: event):
        """
        Interprets the name of an event to extract the title and the time.
        """
        e_str = e.name.split(' ')
        e.beg = e_str[0]
        e.end = e_str[2]
        title = ""
        for i in range(3, len(e_str)):
            title += e_str[i] + " "
        e.name = title

    def get_events(self) -> np.ndarray:
        """
        Extract and return all events from the calendar.

        Returns:
        - numpy array of event objects
        """
        if self.ocr_data is None:
            self.process()

        week, days_x = self._get_weeks(self.ocr_data)
        time_pattern = re.compile(r'\d{2}:\d{2} - \d{2}:\d{2}')

        event_indices = [i for i in range(len(self.ocr_data["text"])) if time_pattern.search(self.ocr_data["text"][i])]
        n = len(event_indices)
        events = np.zeros(n, dtype=event)

        for idx, i in enumerate(event_indices):
            name = self.ocr_data["text"][i]
            x, y, w, h = self.ocr_data["left"][i], self.ocr_data["top"][i], self.ocr_data["width"][i], self.ocr_data["height"][i]
            b = box(x, y, w, h)
            events[idx] = event(name, box=b)

        for e in events:
            e.getWeekdayFromTable(days_x, week)
            self._interpret_event_name(e)

        self.events = events
        return events


def draw_box(draw, box_coords, flag, width=2):
    """
    Draws bounding boxes on an image.

    Parameters:
    - draw: ImageDraw.Draw object
    - box_coords: array, [x, y, width, height]
    - flag: 0 for red, 1 for green
    - width: line width
    """
    x, y, w, h = box_coords
    color = 'green' if flag else 'red'
    draw.rectangle([x, y, x + w, y + h], outline=color, width=width)
