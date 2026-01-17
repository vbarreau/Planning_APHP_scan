"""
GoogleAuth class for handling Google Calendar API authentication and operations.
"""

import os
import configparser
from tkinter import filedialog

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError


class GoogleAuth:
    """
    Handles Google Calendar API authentication and calendar operations.
    Constructed with a config file path, loads configuration and manages credentials.
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, config_path: str | None = None):
        """
        Initialize GoogleAuth with configuration from a config file.

        Parameters:
        - config_path: Path to the config.ini file. If None, uses default location.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.ini")

        self.config_path = config_path
        self.config = self._load_config()
        self.google_account = self.config.get("Google", "account", fallback=None)
        self.calendars = None
        self._creds = None

    def _load_config(self) -> configparser.ConfigParser:
        """Load configuration from config.ini file."""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path)
        return config

    def _check_token(self, path_list: list) -> tuple:
        """
        Check if the token.json file exists and load the credentials.

        Parameters:
        - path_list: List of potential paths to token.json

        Returns:
        - Tuple of (credentials, token_path)
        """
        creds = None
        token_path = ""

        for path in path_list:
            if os.path.exists(path):
                token_path = path
                break

        if token_path:
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

        return creds, token_path

    def setup(self) -> 'GoogleAuth':
        """
        Set up the Google API connection and authenticate.

        Returns:
        - self for method chaining
        """
        creds, token_path = self._check_token([
            "token.json",
            "D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/token.json"
        ])

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    # Token is invalid, need to re-authenticate
                    os.remove(token_path)
                    creds = None

            if not creds:
                creds_path = self._find_credentials_file()
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        self._creds = creds
        self.service = build("calendar", "v3", credentials=creds)

        return self

    def _find_credentials_file(self) -> str:
        """
        Find the credentials.json file, prompting user if not found in default locations.

        Returns:
        - Path to credentials.json
        """
        if os.path.exists("credentials.json"):
            return "credentials.json"
        elif os.path.exists("D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/credentials.json"):
            return "D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources/credentials.json"
        else:
            return filedialog.askopenfilename(
                title="Indiquez credentials.json",
                filetypes=[("JSON file", "*.json")],
                initialdir="D:/OneDrive/Documents/11 - Codes/HDJ_scan/ressources",
                initialfile="",
                defaultextension="*.json",
            )

    def get_calendars(self) -> list:
        """
        Fetches the list of available calendars from the Google account.

        Returns:
        - List of tuples (calendar_id, calendar_name)
        """
        if not self.service :
            self.setup()

        try:
            calendar_list = self.service.calendarList().list().execute().get('items', []) # type: ignore
            calendars = []
            for calendar in calendar_list:
                cal_id = calendar['id']
                cal_name = calendar.get('summary', cal_id)
                calendars.append((cal_id, cal_name))
            self.calendars = calendars
        except HttpError as error:
            print(f"Error fetching calendars: {error}")
            calendars = []

        return calendars

    def create_event(self, title: str, beg: str, end: str, calendar_id: str | None = None):
        """
        Creates an event in the specified calendar.

        Parameters:
        - title: Event title
        - beg: Start datetime in ISO format (e.g., '2026-01-01T09:00:00')
        - end: End datetime in ISO format
        - calendar_id: Target calendar ID. If None, uses the default account.
        """
        if not self.service:
            self.setup()

        if calendar_id is None:
            calendar_id = self.google_account

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

        event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))

    def export_event(self, event, calendar_id: str | None = None):
        """
        Creates a calendar event from an event object.

        Parameters:
        - event: Event object with name, day, beg, end attributes
        - calendar_id: Target calendar ID
        """
        date_beg = f"{event.day}T{event.beg}:00"
        date_end = f"{event.day}T{event.end}:00"
        self.create_event(event.name, date_beg, date_end, calendar_id)

    def export_events(self, events_array, calendar_id: str | None = None) -> list:
        """
        Exports multiple events to Google Calendar.

        Parameters:
        - events_array: Array of event objects
        - calendar_id: Target calendar ID

        Returns:
        - List of events that failed to export
        """
        errors = []
        for event in events_array:
            if event.flag == 1:
                try:
                    self.export_event(event, calendar_id)
                except Exception as e:
                    print(f"Failed to create event '{event.name}': {e}")
                    errors.append(event)
        return errors
