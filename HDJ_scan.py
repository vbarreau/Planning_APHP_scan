import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os
import numpy as np
import re
import fitz  # PyMuPDF for PDF processing
from PIL import Image, ImageDraw
import pytesseract
import matplotlib.pyplot as plt

"""
This program reads a somewhat messy PDF schedule and exports it to a Google calendar. 

To make it work correctly, follow the procedure indicated on https://developers.google.com/calendar/api/quickstart/python
A Google Cloud project needs to be set up and a credentials.json file saved in the home folder.

"""

#############   SET UP   ##################

MONTHS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
GOOGLE_ACCOUNT = "account@gmail.com"

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())
try:
    service = build("calendar", "v3", credentials=creds)
except HttpError as error:
    print(f"An error occurred: {error}")


############  FUNCTIONS  ################


def create_event(title: str, beg: str, end: str):
    """Crée un évènement dans le calendrier référencé par l'API"""

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


def visualize_text_positions(img, ocr_data, output_image="output.png", lines=[], columns=[]):
    """
    Draws bounding boxes around detected text from OCR.
    """
    draw = ImageDraw.Draw(img)

    for i in range(len(ocr_data)):
        x, y, w, h, text = ocr_data[i]
        draw.rectangle([x, y, x + w, y + h], outline="red", width=2)
    for x in lines:
        draw.line([0, x, img.width, x], fill='red')
    for y in columns:
        draw.line([y, 0, y, img.width], fill='red')

    # Save and display the image
    img.save(output_image)
    plt.imshow(img)
    plt.axis("off")
    #   plt.show()


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
    img = pdf_to_image(pdf)
    data = extract(img)
    columns = data[np.where(data[:, -1] == 'KINESITHERAPEUTE'), 0][0] - 10
    time_pattern = re.compile(r'\d\d:00')
    matches = np.array([bool(re.fullmatch(time_pattern, s)) for s in data[:, -1]])

    # regroup sentences
    data = group_lines(data, x_threshold=300, y_threshold=50, columns=columns)
    # visualize_text_positions(img, data, output_image='step1.png', columns=columns)

    # regroup logical boxes. This two step process allow for sligthly more efficient computuation.
    data2 = group_boxes(data, y_threshold=75, columns=columns)

    # visualize_text_positions(img, data2, output_image='step2.png') #debug
    return data2[:, (0, -1)]


def get_days_i(strings):
    """ 
    returns the indices of the french dates strings in a list of strings.
    """
    date_pattern = re.compile(r'\b\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b', re.IGNORECASE)
    indices = [i for i, s in enumerate(strings) if date_pattern.search(s) and "Le" not in s]

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


def sort_planning(s: np.ndarray):
    """ 
    From get_string_planning raw data, formats a planning : a list of events with a column per day of the week.
    """
    days_i = get_days_i(s[:, -1])
    days_x = s[days_i, 0]

    time_pattern = re.compile(r'\d{2}:\d{2} - \d{2}:\d{2}')
    events_s = [[s[i, 0], s[i, 1]] for i in range(len(s)) if time_pattern.search(s[i, 1])]
    events_s = np.array(events_s, dtype=object)
    planning = [[], [], [], [], []]
    for i in range(len(events_s)):
        spots = np.where(days_x >= events_s[i, 0])[0]
        if len(spots) > 0:
            planning[spots[0]].append(events_s[i, 1])

    week = []
    for i in range(5):
        week.append(compact_string_day(s[days_i[i], -1]))

    return planning, week


def string_to_event(event_s, compact_day):
    """
    Creates an event on Google calendar.
    envent_s : str, '00:00 - 01:00 Title of event
    compact day : str, 2025-01-01
    """
    e = event_s.split(' ')
    time_beg = e[0]
    time_end = e[2]
    title = ""
    for i in range(3, len(e)):
        title += e[i] + " "
    date_beg = compact_day + "T" + time_beg + ":00"
    date_end = compact_day + "T" + time_end + ":00"

    create_event(title, date_beg, date_end)


def planning_to_google(planning, week):
    for i in range(5):
        for event in planning[i]:
            string_to_event(event, week[i])


def pdf_to_google(pdf):
    string_data = get_string_planning(pdf)
    p, week = sort_planning(string_data)
    planning_to_google(p, week)


if __name__ == "__main__":
    string_data = get_string_planning('test.pdf')
    p, week = sort_planning(string_data)
    string_to_event(p[2][1], week[2])