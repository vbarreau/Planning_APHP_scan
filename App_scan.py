from HDJ_scan import *
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image, ImageDraw

""" 
Ce fichier controle l'asect interractif de l'application. Tout ce qui est visuelle, boutons, etc... est codé ici."""

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

def proceed_button(win,events_array):
    planning_to_google(events_array)
    win.destroy()

def new_text_entry(root,text,default):
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
    win.geometry('1500x1000')
    win.configure(bg="white")
    
    file_path = filedialog.askopenfilename(
            title="Sélectionnez votre planning", 
            filetypes=(("pdf files", "*.pdf"),("images", "*.png *.jpg")),
            initialdir="C:/Users/vbarr/Downloads",
            initialfile="",
            defaultextension="*.pdf",
            multiple=False,
        )
    if not file_path:
        return  # Exit if no file is selected

    img = pdf_to_image(file_path)
    string_data = get_string_planning(file_path)
    events_array = sort_planning(string_data)    

    draw = draw_image(img, events_array)

    img_label = Label(win, bg="white", background="white", activebackground="white", fg="white")

    # Create a frame to hold the checkboxes
    checkbox_frame = Frame(win, bg="white")
    checkbox_frame.grid(row=4, column=0, sticky="nsew", pady=10)    

    check_all_val = IntVar(value=1, name="check_all")
    check_all_button = Checkbutton(checkbox_frame,
                                   variable=check_all_val, 
                                   text="Tout cocher",
                                   onvalue=1, offvalue=0, 
                                   command=lambda: check_all(events_array, list_var_check, check_all_val.get(), img, img_label),
                                   bg="white")
    check_all_button.grid(row=0, column=0, padx=1)

    weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

    week_frames = [Frame(checkbox_frame, padx=5, pady=5, bg="white") for _ in range(5)]
    for i in range(5):
        week_frames[i].grid(row=1, column=i, padx=5, pady=5, sticky="nsew")
        week_label = Label(week_frames[i], text=weekdays[i], bg="white")
        week_label.grid(row=0, column=0)

    img_label.grid(row=5, column=0, padx=5, pady=5, sticky="nsew")

    display_image(img, events_array, img_label)

    list_var_check = [IntVar(value=e.flag) for e in events_array]
    list_case = []

    count = [0] * 5
    for i, e in enumerate(events_array):
        count[e.weekday()] += 1
        button = Checkbutton(week_frames[e.weekday()], text=e.name, 
                variable=list_var_check[i], 
                onvalue=1, 
                offvalue=0, 
                command=lambda i=i: update_img_tk(img, img_label, events_array, i),
                bg="white")
        button.grid(row=count[e.weekday()], column=0, pady=2, sticky="w")
        list_case.append(button)

        edit_button = Button(week_frames[e.weekday()], 
                             text="...", 
                             command=lambda i=i: edit_window(events_array[i], list_case[i]))
        edit_button.grid(row=count[e.weekday()], column=1, pady=2, sticky="w")

    B1 = Button(win, text='Envoyer à Google', command=lambda: proceed_button(win, events_array))
    B1.grid(row=6, column=0, padx=5, pady=5, sticky="nsew")

    # Configure grid weights for resizing
    win.grid_rowconfigure(4, weight=1)  # Checkbox frame row
    win.grid_rowconfigure(5, weight=3)  # Image label row
    win.grid_columnconfigure(0, weight=1)  # Main column

    checkbox_frame.grid_columnconfigure(0, weight=1)  # Check-all button column
    for i in range(5):
        checkbox_frame.grid_columnconfigure(i, weight=1)  # Weekday frames

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
    Si le planning est mal lu, il faut modifier le fichier HDJ_scan.py. En particulier les fonctions get_separators() et get_string_planning()."""
    instructions_label = Label(win_tuto, text=instructions, justify=LEFT, bg="white")
    instructions_label.pack(pady=10, padx=10)
    text_label = Label(win_tuto, text=text, justify=LEFT, bg="white")
    text_label.pack(pady=10, padx=10)

    # Add an image (example image path, replace with actual path)
    try:
        img = Image.open("supercloud.svg")
        img = img.resize((600, 400))
        img_tk = ImageTk.PhotoImage(img)
        img_label = Label(win_tuto, image=img_tk, bg="white")
        img_label.image = img_tk  # Keep a reference to avoid garbage collection
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

    B_scan = Button(win_main, text='Scanner', command= lambda : app_scan(win_main), padx=5, pady=5)
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