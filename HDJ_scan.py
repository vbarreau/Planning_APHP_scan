import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

import os
import numpy as np
import re
import fitz  # PyMuPDF for PDF processing
from PIL import Image, ImageDraw
import pytesseract
import matplotlib.pyplot as plt
from tkinter import filedialog


from scanner import *

"""
This program reads a somewhat messy PDF schedule and exports it to a Google calendar. 
Here are all the functions to do so, but App_scan.py is the main file to run as it contains the GUI and the interactive part of the program.

To make it work correctly, follow the procedure indicated on https://developers.google.com/calendar/api/quickstart/python
A Google Cloud project needs to be set up and a credentials.json file saved in the home folder.

"""

#############   SET UP   ##################

MONTHS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
GOOGLE_ACCOUNT = "vbarreau78@gmail.com"

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


############  FUNCTIONS  ################

def check_token(path_list):
    """
    Check if the token.json file exists and load the credentials."""
    creds = None
    token_path = ""
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    for path in path_list :
        if os.path.exists(path):
            token_path = path
    if token_path != "" :
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return creds, token_path
    

def set_up_google():
    """
    Set up the Google API
        """
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds, token_path = check_token(["token.json","D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/token.json"])
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try :
                creds.refresh(Request())
            except RefreshError :
                os.remove(token_path)
                creds , token_path = check_token([])
                creds.refresh(Request())
        else:
            if os.path.exists( "credentials.json"):
                creds_path =  "credentials.json"

            elif os.path.exists("D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/credentials.json") :
                creds_path = "D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/credentials.json"
            else :
                creds_path = filedialog.askopenfilename(
                            title="Indiquez credentials.json", 
                            filetypes=(("JSON file", "*.json")),
                            initialdir="D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources",
                            initialfile="",
                            defaultextension="*.pdf",
                            multiple=False,
                        )
            flow = InstalledAppFlow.from_client_secrets_file(
               creds_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
    except HttpError as error:
        print(f"An error occurred: {error}")
    return service


def create_event(title: str, beg: str, end: str,service=set_up_google()):
    """Creates an event in the calendar referenced by the API"""

    event = {
        'summary': title,
        'start': {
            'dateTime': beg,
            'timeZone': 'Europe/Paris',
        },
        'end': {
            'dateTime': end,
            'timeZone': 'Europe/Paris',
        },
        'reminders': {
            'useDefault': True,
        },
    }
    # print(service.calendarList().list().execute())
    event = service.events().insert(calendarId=GOOGLE_ACCOUNT, body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))



def pdf_to_image(pdf_path, dpi=300):
    """
    Converts a PDF page to a high-resolution image (PNG format).
    """
    if pdf_path[-3:] == "png" or pdf_path[-3:] == "jpg":
        img =  Image.open(pdf_path)
        # img = process(img)
        return img

    doc = fitz.open(pdf_path)
    page = doc[0]

    # Convert PDF to high-quality image
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    return img


def extract_text_from_image(image):
    """
    Uses Tesseract OCR to extract text from an image.
    """
    text = pytesseract.image_to_string(image, lang="eng")  # Language doesn't matter so much
    return text

def draw_box(draw, box, flag, width=2):
    """
    Draws bounding boxes on an image.

    draw : ImageDraw.Draw()
    box : array, [x, y, width, height]
    """
    x, y, w, h = box
    if flag == 0:
        color = 'red'
    else:
        color = 'green'
    draw.rectangle([x, y, x + w, y + h], outline=color, width=width)


def visualize_text_positions(img, ocr_data, output_image="output.png", lines=[], columns=[]):
    """
    Draws bounding boxes around detected text from OCR.

    img : PIL.Image
    ocr_data : 2D array, [x, y, w, h, text] for each box
    """
    draw = ImageDraw.Draw(img)

    for i in range(len(ocr_data)):
        draw_box(draw, ocr_data[i,:4], flag=1)
    for x in lines:
        draw.line([0, x, img.width, x], fill='red')
    for y in columns:
        draw.line([y, 0, y, img.width], fill='red')

    # Save and display the image
    img.save(output_image)
    plt.imshow(img)
    plt.axis("off")
    #   plt.show()

def visualize_events(img, events_array,line = None,column=None):
    draw = ImageDraw.Draw(img)

    for i in range(len(events_array)):
        e = events_array[i]
        b = e.box
        draw_box(draw, b.unpack(), flag=e.flag)
    
    if line is not None :
        for l in line :
            draw.line([0, l, img.width, l], fill='blue')
    if column is not None:
        for c in column:
            draw.line([c, 0, c, img.height], fill='blue')
    
    # Save and display the image
    plt.imshow(img)
    plt.axis("off")

def extract(img):
    """
    Extract text from image with pytesseract
    """
    ocr_data = []
    ocr_results = pytesseract.image_to_data(img, lang="eng", output_type=pytesseract.Output.DICT)
    for i in range(len(ocr_results["text"])):
        if ocr_results["text"][i].strip():  # Ignore empty results
            x, y, w, h = (int(ocr_results["left"][i]), int(ocr_results["top"][i]),
                          int(ocr_results["width"][i]), int(ocr_results["height"][i]))
            text = ocr_results["text"][i]
            ocr_data.append((x, y, w, h, text))
    ocr_data = np.array(ocr_data,dtype=object)
    return ocr_data

def get_separators(image) :

    """
    Identifies the horizontal and vertical separators in the image.
    """
    img_array = np.array(image.convert("L"))  # Convert image to grayscale
    img_array = 255 - img_array  # Invert colors: text becomes white, background becomes black

    # Sum pixel values along the vertical and horizontal axes
    vertical_sum = np.sum(img_array, axis=0)
    horizontal_sum = np.sum(img_array, axis=1)

    critere_line = 255*image.width/2
    critere_col = 255*image.height/3

    # Identify columns and lines based on pixel intensity thresholds
    columns = np.where(vertical_sum > critere_col)[0]
    lines = np.where(horizontal_sum > critere_line)[0]

    # draw = ImageDraw.Draw(image)
    # for x in columns:
    #     draw.line([x, 0, x, image.height], fill='red')
    # for y in lines:
    #     draw.line([0, y, image.width, y], fill='red')
    # plt.imshow(image)
    # plt.axis("off")
    # plt.show()

    return lines, columns

def extract_and_visualize(pdf_path):
    """
    Full pipeline: PDF to Image → OCR Extraction → Visualization.
    """
    img = pdf_to_image(pdf_path)
    ocr_data = extract(img)
    visualize_text_positions(img, ocr_data)

def within_columns(x1, x2, columns):
    """
    check wether a text is in a column (True) or across several (False)
    """
    if columns is None:
        return True
    for col in columns:
        if x1 <= col <= x2 or x2 <= col <= x1:
            return False
    return True


def combine_box(box1, box2, out):
    x1, y1, w1, h1, text1 = box1
    x2, y2, w2, h2, text2 = box2
    combined_text = text1 + " " + text2
    combined_width = max(x1 + w1, x2 + w2) - min(x1, x2)
    combined_height = max(y1 + h1, y2 + h2) - min(y1, y2)
    out.append([min(x1, x2), min(y1, y2), combined_width, combined_height, combined_text])


def group_lines(data, x_threshold=300, y_threshold=50, columns=None, lines=None):
    """
    Cleans the data by combining text boxes that are close enough to form a single sentence.
    Text is read from left to right, top to bottom. sentences should not go across lines or columns defined.
    ~ O(n)
    Parameters:
    - data: numpy array of OCR data with each element in the format [x, y, w, h, text]
    - x_threshold: maximum horizontal distance between boxes to be combined
    - y_threshold: maximum vertical distance between boxes to be combined
    - columns: list of x-coordinates defining column boundaries

    Returns:
    - cleaned_data: numpy array of cleaned OCR data
    """
    n = len(data)
    combined = True

    while combined:
        combined = False
        out = []
        i = n - 1
        while i > 0:
            x1, y1, w1, _, _ = data[i - 1]
            x2, y2, _, _, _ = data[i]
            if abs(x2 - (x1 + w1)) < x_threshold and abs(y2 - y1) < y_threshold and within_columns(x1, x2, columns) and within_columns(y1, y2, lines):
                combine_box(data[i - 1], data[i], out)
                i -= 2  # Skip the previous element as it has been combined
                combined = True
            else:
                out.append(data[i])
                i -= 1
        if i == 0:  # Append the first element if it wasn't combined
            out.append(data[i])
        data = np.array(out[::-1], dtype=object)  # Reverse the list to maintain original order
        n = len(data)

    return data


def group_boxes(data, x_threshold=150, y_threshold=75, columns=None, lines=None):
    """
    Cleans the OCR data by combining text boxes that are close enough to form a single text area. ~ O(n²)

    Parameters:
    - data: numpy array of OCR data with each element in the format [x, y, w, h, text]
    - x_threshold: maximum horizontal distance between boxes to be combined
    - y_threshold: maximum vertical distance between boxes to be combined
    - columns: list of x-coordinates defining column boundaries

    Returns:
    - cleaned_data: numpy array of cleaned OCR data
    """
    n = len(data)
    combined_indices = set()
    out = []

    for i in range(n):
        if i in combined_indices:
            continue
        x1, y1, w1, h1, text1 = data[i]
        combined_text = text1
        combined_x1, combined_y1 = x1, y1
        combined_x2, combined_y2 = x1 + w1, y1 + h1

        for j in range(i + 1, n):
            if j in combined_indices:
                continue
            x2, y2, w2, h2, text2 = data[j]
            if abs(x2 - x1) < x_threshold and abs(y2 - y1) < y_threshold and within_columns(x1, x2, columns) and within_columns(y1, y2, lines):
                combined_text += " " + text2
                combined_x1 = min(combined_x1, x2)
                combined_y1 = min(combined_y1, y2)
                combined_x2 = max(combined_x2, x2 + w2)
                combined_y2 = max(combined_y2, y2 + h2)
                combined_indices.add(j)

        combined_width = combined_x2 - combined_x1
        combined_height = combined_y2 - combined_y1
        out.append([combined_x1, combined_y1, combined_width, combined_height, combined_text])

    cleaned_data = np.array(out, dtype=object)
    return cleaned_data


def get_string_planning(pdf):
    """ 
    Extracts and cleans the data from the pdf.
    returns : ndarray - 0 is x position of the text, 1 is the text
    """
    if pdf[-3:] == 'pdf':
        img = pdf_to_image(pdf)
    elif pdf[-3:] == 'png' or pdf[-3:] == 'jpg':
        img = Image.open(pdf)
    else:
        print("\nFile format not supported\n")
        return FileNotFoundError
    
    data = extract(img)
    
    lines, columns = get_separators(img)
    # regroup sentences
    data = group_lines(data, x_threshold=300, y_threshold=50, columns=columns)
    # visualize_text_positions(img, data, output_image='step1.png', columns=columns)

    # regroup logical boxes. This two step process allow for sligthly more efficient computuation.
    data2 = group_boxes(data, y_threshold=75, columns=columns)


    # visualize_text_positions(img, data2, output_image='step2.png') #debug
    return data2


def get_days_i(strings):
    """ 
    Returns the indices of the French date strings in a list of strings, ensuring they are in order.
    """
    date_pattern = re.compile(r'\b\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b', re.IGNORECASE)
    indices = [i for i, s in enumerate(strings) if date_pattern.search(s) and "Le" not in s]

    # Sort indices to ensure they are in order
    indices.sort(key=lambda i: strings[i])

    return indices


def compact_string_day(s: str):
    """
    Converts (returns) a date from "weekday num month" (french) to a datetime format (2025)
    """
    l = s.split(sep=' ')
    num = int(l[1])
    month_num = MONTHS.index(l[2]) + 1
    compacted_date = f"2025-{month_num:02d}-{num:02d}"
    return compacted_date


def interpret_event_name(e:event):
    """
    Interprets the name of an event to extract the title and the time of the event.
    """
    e_str = e.name.split(' ')
    e.beg = e_str[0]
    e.end = e_str[2]
    title = ""
    for i in range(3, len(e_str)):
        title += e_str[i] + " "
    e.name = title


def get_weeks(data: np.ndarray):
    """ 
    From get_string_planning raw data, returns the weeks of the planning.
    """
    s = data[:,(0,-1)]

    # I identify which area of the document corresponds to which day of the week
    days_i = get_days_i(s[:, -1])
    days_i_sorted = np.zeros(len(days_i),dtype=int)
    for i in days_i :
        if "lundi" in s[i, -1].lower():
            days_i_sorted[0] = i
        elif "mardi" in s[i, -1].lower():
            days_i_sorted[1] = i
        elif "mercredi" in s[i, -1].lower():
            days_i_sorted[2] = i
        elif "jeudi" in s[i, -1].lower():
            days_i_sorted[3] = i
        elif "vendredi" in s[i, -1].lower():
            days_i_sorted[4] = i
    days_x = s[days_i_sorted, 0]
    
    week = []
    try:
        for i in range(5):
            week.append(compact_string_day(s[days_i_sorted[i], -1]))
    except:
        print("Impossible de lire le planning. Si le fichier d'entrée est une photo, considérez utiliser une capture d'écran.")
    return week, days_x


def sort_planning(data: np.ndarray):
    """ 
    From get_string_planning raw data, formats a planning : a list of events with a column per day of the week.
    """
    s = data[:,(0,-1)]
    week, days_x = get_weeks(data)

    # A text represents an event if it contains a time pattern
    time_pattern = re.compile(r'\d{2}:\d{2} - \d{2}:\d{2}')
    events_data = np.array([data[i] for i in range(len(s)) if time_pattern.search(s[i, 1])])
    n = len(events_data)
    events = np.zeros(n, dtype=event)
    for i in range(len(events)):
        name = events_data[i,-1]
        x,y,w,h = events_data[i,:-1]
        b2 = box(x,y,w,h)
        events[i] = event(name,box=b2)

    for i in range(len(events)):
        spots = np.where(days_x >= events[i].box.x)[0]
        if len(spots) > 0:
            events[i].day = week[spots[0]]
        interpret_event_name(events[i])
    return events


def string_to_event(e:event):
    """
    Creates an event on Google calendar.
    envent_s : str, '00:00 - 01:00 Title of event'
    compact day : str, 2025-01-01
    """
    assert type(e) == event
    

    date_beg = e.day + "T" + e.beg + ":00"
    date_end = e.day + "T" + e.end + ":00"

    create_event(e.name, date_beg, date_end)


def planning_to_google(events_array):
    for event in events_array:
        if event.flag == 1:
            string_to_event(event)


def file_to_google(pdf):
    string_data = get_string_planning(pdf)
    events_array = sort_planning(string_data)
    planning_to_google(events_array)


if __name__ == "__main__":
    # debug 
    file = filedialog.askopenfilename()
    img = pdf_to_image(file)
    string_data = get_string_planning(file)
    events_array = sort_planning(string_data)
    line,col = get_separators(img)
    visualize_events(img, events_array,line,col)
    plt.show()