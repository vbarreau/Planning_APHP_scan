from calendar_reader import CalendarReader, draw_box
from google_auth import GoogleAuth
from tkinter import filedialog, Label, Entry, Button, Checkbutton, IntVar, Frame, Tk, LEFT, StringVar
from tkinter.ttk import Combobox
from PIL import ImageTk, Image, ImageDraw
import numpy as np


def draw_image(img, events_array):
    plot = img.copy()
    draw = ImageDraw.Draw(plot)
    for i in range(len(events_array)):
        b = events_array[i].box
        draw_box(draw, b.to_draw(), events_array[i].flag)
    return plot


def display_image(img, events_array, img_label):
    plot = draw_image(img, events_array)
    img_small = plot.resize((800, 600))
    img_tk = ImageTk.PhotoImage(img_small)
    img_label.config(image=img_tk)
    img_label.image = img_tk  # Keep a reference to avoid garbage collection


def update_img_tk(img, img_label, p, i):
    val = p[i].flag
    if val == 1:
        p[i].flag = 0
    else:
        p[i].flag = 1
    display_image(img, p, img_label)


def edit_error_event(event, label, error_win):
    """Opens an edit window for a failed event and updates the label after saving."""
    edit_win = Tk()
    edit_win.title('Modifier l\'événement')
    edit_win.geometry('400x300')
    edit_win.configure(bg="white")

    name_entry = new_text_entry(edit_win, "Nom:", event.name)
    day_entry = new_text_entry(edit_win, "Jour (AAAA-MM-JJ):", event.day)
    beg_entry = new_text_entry(edit_win, "Début (HH:MM):", event.beg)
    end_entry = new_text_entry(edit_win, "Fin (HH:MM):", event.end)

    def save_changes():
        event.name = name_entry.get()
        event.day = day_entry.get()
        event.beg = beg_entry.get()
        event.end = end_entry.get()
        label.config(text=f"- {event.name} ({event.day} {event.beg}-{event.end})")
        edit_win.destroy()

    Button(edit_win, text="Enregistrer", command=save_changes, padx=10, pady=5).pack(pady=15)

    edit_win.mainloop()


def proceed_button(win, events_array, auth: GoogleAuth, calendar_id=None):
    export_errors = auth.export_events(events_array, calendar_id)
    if len(export_errors) > 0:
        show_error_window(export_errors, auth, calendar_id)
    win.destroy()


def show_error_window(export_errors, auth: GoogleAuth, calendar_id):
    """Displays a window with failed events, allowing editing and retry."""
    error_win = Tk()
    error_win.title('Erreurs d\'exportation')
    error_win.geometry('500x400')
    error_win.configure(bg="white")

    Label(error_win, text="Les événements suivants n'ont pas pu être exportés :",
          bg="white", font=("Segoe UI", 10, "bold")).pack(pady=10)

    # Frame for the list of errors
    list_frame = Frame(error_win, bg="white")
    list_frame.pack(fill="both", expand=True, padx=10)

    event_labels = []
    for e in export_errors:
        row_frame = Frame(list_frame, bg="white")
        row_frame.pack(fill="x", pady=2)

        label = Label(row_frame, text=f"- {e.name} ({e.day} {e.beg}-{e.end})",
                      bg="white", anchor="w", font=("Segoe UI", 9))
        label.pack(side=LEFT, fill="x", expand=True)
        event_labels.append(label)

        edit_btn = Button(row_frame, text="✏️ Modifier",
                          command=lambda ev=e, lbl=label: edit_error_event(ev, lbl, error_win),
                          font=("Segoe UI", 8), relief="flat", bg="#e0e0e0")
        edit_btn.pack(side=LEFT, padx=5)

    # Button frame at the bottom
    btn_frame = Frame(error_win, bg="white")
    btn_frame.pack(fill="x", pady=15)

    def retry_export():
        error_win.destroy()
        new_errors = auth.export_events(export_errors, calendar_id)
        if len(new_errors) > 0:
            show_error_window(new_errors, auth, calendar_id)

    Button(btn_frame, text="Réessayer l'export", command=retry_export,
           font=("Segoe UI", 10, "bold"), bg="#4285f4", fg="white",
           padx=15, pady=5, relief="flat").pack(side=LEFT, padx=10)

    Button(btn_frame, text="Fermer", command=error_win.destroy,
           font=("Segoe UI", 10), padx=15, pady=5).pack(side=LEFT)

    error_win.mainloop()


def new_text_entry(root, text, default):
    Label(root, text=text).pack()
    entry = Entry(root, width=30)
    entry.insert(0, default)
    entry.pack()
    return entry


def edit_window(event, checkbox):
    win = Tk()
    win.title('Edit')
    win.geometry('500x500')

    name_entry = new_text_entry(win, "Name:", event.name)
    beg_entry = new_text_entry(win, "Begin Time:", event.beg)
    end_entry = new_text_entry(win, "End Time:", event.end)
    day_entry = new_text_entry(win, "Day:", event.day)

    def save_changes():
        event.name = name_entry.get()
        event.beg = beg_entry.get()
        event.end = end_entry.get()
        event.day = day_entry.get()
        checkbox.config(text=event.name)
        win.destroy()

    save_button = Button(win, text="Save", command=save_changes)
    save_button.pack()


def check_all(events_array, list_var, val, img, img_label):
    assert val == 0 or val == 1
    for var in list_var:
        var.set(val)
    for e in events_array:
        e.flag = val
    display_image(img, events_array, img_label)


def app_scan(win):
    # Clear existing widgets from home screen
    for widget in win.winfo_children():
        widget.destroy()

    # Initialize GoogleAuth and set up connection
    auth = GoogleAuth()
    auth.setup()
    calendars = auth.get_calendars()

    if calendars is None or len(calendars) == 0:
        Label(win, text="Aucun calendrier trouvé. Vérifiez votre connexion.", bg="white").pack()
        return

    file_path = filedialog.askopenfilename(
        title="Sélectionnez votre planning",
        filetypes=(("pdf files", "*.pdf"), ("images", "*.png *.jpg")),
        initialdir="C:/Users/vbarr/Downloads",
        initialfile="",
        defaultextension="*.pdf",
    )
    if not file_path:
        return

    win.geometry('1500x900')
    win.configure(bg="white")

    # Main container frame
    main_frame = Frame(win, bg="white")
    main_frame.pack(fill="both", expand=True, padx=15, pady=10)

    # Top section: Calendar selection
    cal_frame = Frame(main_frame, bg="white", relief="groove", bd=1)
    cal_frame.pack(fill="x", pady=(0, 10))

    cal_inner = Frame(cal_frame, bg="white")
    cal_inner.pack(pady=8, padx=10)

    Label(cal_inner, text="Calendrier cible:", bg="white", font=("Segoe UI", 10)).pack(side=LEFT, padx=5)

    calendar_var = StringVar()
    calendar_names = [name for _, name in calendars]
    calendar_ids = {name: cal_id for cal_id, name in calendars}

    cal_combo = Combobox(cal_inner, textvariable=calendar_var, values=calendar_names, state="readonly", width=40)
    cal_combo.set(calendar_names[0])
    cal_combo.pack(side=LEFT, padx=5)

    # Use CalendarReader to process the file
    reader = CalendarReader(file_path)
    img = reader.load_image()
    reader.get_separators()
    events_array = reader.get_events()

    # Middle section: Checkboxes for events
    checkbox_frame = Frame(main_frame, bg="white", relief="groove", bd=1)
    checkbox_frame.pack(fill="x", pady=(0, 10))

    # Header with "Select All" checkbox
    header_frame = Frame(checkbox_frame, bg="#f0f0f0")
    header_frame.pack(fill="x", pady=(0, 5))

    check_all_val = IntVar(value=1, name="check_all")

    # Placeholder for img_label (needed for check_all command)
    img_label = Label(main_frame, bg="white")

    check_all_button = Checkbutton(header_frame,
                                   variable=check_all_val,
                                   text="Tout sélectionner",
                                   onvalue=1, offvalue=0,
                                   command=lambda: check_all(events_array, list_var_check, check_all_val.get(), img, img_label),
                                   bg="#f0f0f0",
                                   font=("Segoe UI", 9, "bold"))
    check_all_button.pack(pady=5, padx=10, anchor="w")

    # Weekday columns container
    weekdays_container = Frame(checkbox_frame, bg="white")
    weekdays_container.pack(fill="x", padx=10, pady=(0, 10))

    weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

    week_frames = []
    for i in range(5):
        col_frame = Frame(weekdays_container, bg="white", relief="flat", bd=0)
        col_frame.grid(row=0, column=i, padx=8, pady=5, sticky="n")

        # Day header label with underline effect
        day_label = Label(col_frame, text=weekdays[i], bg="white",
                          font=("Segoe UI", 10, "bold"), fg="#333333")
        day_label.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")

        # Separator line under day name
        sep = Frame(col_frame, bg="#cccccc", height=1)
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        week_frames.append(col_frame)

    # Configure weekdays container columns to distribute evenly
    for i in range(5):
        weekdays_container.grid_columnconfigure(i, weight=1)

    # Action button at the bottom (pack first with side=BOTTOM to ensure visibility)
    button_frame = Frame(main_frame, bg="white")
    button_frame.pack(side="bottom", fill="x", pady=(10, 0))

    # Bottom section: Image display (fills remaining space)
    img_frame = Frame(main_frame, bg="white", relief="groove", bd=1)
    img_frame.pack(fill="both", expand=True, pady=(0, 10))

    img_label.master = img_frame
    img_label.pack(pady=10, padx=10)

    display_image(img, events_array, img_label)

    # Sort events chronologically by day and start time
    events_array = sorted(events_array, key=lambda e: (e.day, e.beg))
    events_array = np.array(events_array)

    list_var_check = [IntVar(value=e.flag) for e in events_array]
    list_case = []

    count = [0] * 7
    for i, e in enumerate(events_array):
        count[e.weekday()] += 1
        # Offset by 2 to account for header label and separator
        row_num = count[e.weekday()] + 1

        button = Checkbutton(week_frames[e.weekday()], text=e.name,
                             variable=list_var_check[i],
                             onvalue=1,
                             offvalue=0,
                             command=lambda i=i: update_img_tk(img, img_label, events_array, i),
                             bg="white",
                             font=("Segoe UI", 9),
                             anchor="w")
        button.grid(row=row_num, column=0, pady=1, sticky="w")
        list_case.append(button)

        edit_button = Button(week_frames[e.weekday()],
                             text="✏️",
                             command=lambda i=i: edit_window(events_array[i], list_case[i]),
                             font=("Segoe UI", 8),
                             width=2,
                             relief="flat",
                             bg="#e0e0e0")
        edit_button.grid(row=row_num, column=1, pady=1, padx=(2, 0), sticky="w")

    def get_selected_calendar_id():
        return calendar_ids.get(calendar_var.get())

    B1 = Button(button_frame, text='Envoyer à Google Calendar',
                command=lambda: proceed_button(win, events_array, auth, get_selected_calendar_id()),
                font=("Segoe UI", 10, "bold"),
                bg="#4285f4", fg="white",
                padx=20, pady=8,
                relief="flat",
                cursor="hand2")
    B1.pack(side=LEFT, padx=10, pady=5)

    B_close = Button(button_frame, text='Fermer',
                     command=win.destroy,
                     font=("Segoe UI", 10),
                     padx=20, pady=8,
                     relief="flat",
                     cursor="hand2")
    B_close.pack(side=LEFT, padx=10, pady=5)

    win.mainloop()


def tuto():
    win_tuto = Tk()
    win_tuto.title('Mise en place - Didacticiel')
    win_tuto.geometry('800x600')
    win_tuto.configure(bg="white")

    # Add a title label
    title_label = Label(win_tuto, text="Mise en place de l'API Google", font=("Helvetica", 16), bg="white")
    title_label.pack(pady=10)

    # Add instructional text
    instructions = """
    1. Créez un projet Google sur : https://console.cloud.google.com/projectcreate
    2. Allez dans la section "API et services" et activez l'API Google Calendar, en haut de la page.
    3. Séléctionnez "Google Calendar API" dans la liste des API disponibles, cliquez sur "gérer" pour l'activer.
    4. Créez des identifiants d'authentification OAuth 2.0.
    5. Créez des identifiants d'authentification OAuth 2.0.
    6. Téléchargez le fichier JSON des identifiants et placez-le dans le répertoire de votre projet.
    7. Installez les bibliothèques nécessaires en utilisant pip:
       pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    8. Le fichier JSON doit être nommé "credentials.json", il sera utilisé pour l'authentification.
    """

    text = """
    Si le planning est mal lu, il faut modifier le fichier calendar_reader.py. En particulier les méthodes get_separators() et process()."""
    instructions_label = Label(win_tuto, text=instructions, justify=LEFT, bg="white")
    instructions_label.pack(pady=10, padx=10)
    text_label = Label(win_tuto, text=text, justify=LEFT, bg="white")
    text_label.pack(pady=10, padx=10)

    # Add an image (example image path, replace with actual path)
    try:
        img = Image.open("supercloud.svg")  # Changed from .svg to .png (PIL doesn't support SVG)
        img = img.resize((600, 400))
        img_tk = ImageTk.PhotoImage(img)
        img_label = Label(win_tuto, image=img_tk, bg="white")
        img_label.pack(pady=10)
    except Exception as e:
        error_label = Label(win_tuto, text="Image non trouvée", bg="white")
        error_label.pack(pady=10)

    # Add a close button
    close_button = Button(win_tuto, text="Fermer", command=win_tuto.destroy, padx=5, pady=5)
    close_button.pack(pady=10)

    win_tuto.mainloop()
    return None


def home():
    win_main = Tk(screenName="Scanneur d'EdT")
    win_main.title('Scan')
    win_main.geometry('300x300')
    win_main.configure(bg="white")

    B_scan = Button(win_main, text='Scanner', command=lambda: app_scan(win_main), padx=5, pady=5)
    B_tuto = Button(win_main, text='Mise en place - Didactitiel', command=tuto, padx=5, pady=5)
    B_quit = Button(win_main, text='Quitter', command=win_main.destroy, padx=5, pady=5)

    B_scan.grid(row=0, column=0, padx=5, pady=5)
    B_tuto.grid(row=1, column=0, padx=5, pady=5)
    B_quit.grid(row=2, column=0, padx=5, pady=5)

    # Center the buttons
    win_main.grid_columnconfigure(0, weight=1)
    win_main.mainloop()


if __name__ == '__main__':
    home()
