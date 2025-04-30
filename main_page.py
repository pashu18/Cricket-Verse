import tkinter as tk
from tkinter import ttk, messagebox, font
import pandas as pd
import os
import winsound
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import plotly.graph_objs as go
import plotly.offline as pyo
import plotly.subplots as sp
import webbrowser
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageGrab
from io import BytesIO
import threading
import logging
import random
import pygame

# Configure logging
logging.getLogger('PIL').setLevel(logging.WARNING)

# Initialize pygame mixer
pygame.mixer.init()

# Color Scheme
BG_COLOR = "#0a2e38"  # Dark teal
SECONDARY_COLOR = "#1a4a5a"  # Medium teal
ACCENT_COLOR = "#f0c14b"  # Gold
BUTTON_COLOR = "#1e6f8c"  # Blue-teal
HOVER_COLOR = "#2a8cb3"  # Lighter blue-teal
TEXT_COLOR = "#ffffff"  # White
ERROR_COLOR = "#e74c3c"  # Red for errors/warnings
CARD_BG = "#1a3a4a"  # Card background
CAPTAIN_COLOR = "#2a4a5a"  # Darker blue for captain
WK_COLOR = "#1a5a4a"  # Greenish for wicketkeeper

# File paths and API setup
file_path = "ACTIVE_INDIAN_CRICKET_PLAYERS(Final)-4.xlsx"
if not os.path.exists(file_path):
    messagebox.showerror("Error", "Dataset file not found!")
    exit()

xls = pd.ExcelFile(file_path)

models = {}
API_KEY = "AIzaSyAoVh3GxgSsV8V7iaMD5YfBrGrkx2akxEM"
SEARCH_ENGINE_ID = "a79ec3a4bb64c4cb6"
IMAGE_CACHE_DIR = "player_images"

if not os.path.exists(IMAGE_CACHE_DIR):
    os.makedirs(IMAGE_CACHE_DIR)

def play_sound(sound_file="click.wav"):
    try:
        winsound.PlaySound(sound_file, winsound.SND_ASYNC)
    except:
        pass

def play_background_music():
    try:
        pygame.mixer.music.load("cricket_crowd.mp3")
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(-1)
    except:
        print("Background music file not found.")

def fetch_player_image(player_name):
    try:
        image_path = os.path.join(IMAGE_CACHE_DIR, f"{player_name}.jpg")
        if os.path.exists(image_path):
            img = Image.open(image_path)
        else:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"q": f"{player_name} cricketer", "key": API_KEY, "cx": SEARCH_ENGINE_ID, "searchType": "image", "num": 1}
            response = requests.get(url, params=params)
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                image_url = data["items"][0]["link"]
                image_data = requests.get(image_url).content
                with open(image_path, "wb") as f:
                    f.write(image_data)
                img = Image.open(BytesIO(image_data))
            else:
                img = Image.open("PnP_logo.jpg")
        
        img = img.resize((120, 120), Image.Resampling.LANCZOS)
        mask = Image.new("L", (120, 120), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 120, 120), fill=255)
        img.putalpha(mask)
        return img
    except Exception as e:
        print(f"Error fetching image for {player_name}: {e}")
        return Image.open("PnP_logo.jpg")

def clean_data(df, format_type):
    df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace("'", "")
    if 'Player' not in df.columns:
        df['Player'] = "Unknown Player"
    required_columns = {'Centuries': '100s', 'Fifties': '50s', 'Matches': 'Matches', 'Notouts': 'Notouts', 'Balls_Faced': 'Balls_Faced', '4s': '4s', '6s': '6s', 'Ducks': 'Ducks'}
    for new_col, old_col in required_columns.items():
        if old_col in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
    for col in required_columns.keys():
        if col not in df.columns:
            df[col] = 0
    numeric_cols = ['Runs', 'Average', 'Strike_Rate', 'Wickets', 'Economy', 'Centuries', 'Fifties', 'Matches', 'High_Score', 'Notouts', 'Balls_Faced', '4s', '6s', 'Ducks']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ensure Economy column exists and has proper values
    if 'Economy' not in df.columns:
        df['Economy'] = 0.0
    else:
        df['Economy'] = df['Economy'].fillna(0.0)
    
    return df

def train_model(root, progress):
    global models
    models = {}
    for format_type in ["TEST", "ODI", "T20"]:
        try:
            batsmen_df = clean_data(pd.read_excel(xls, sheet_name=f'{format_type} BATSMAN'), format_type)
            bowlers_df = clean_data(pd.read_excel(xls, sheet_name=f'{format_type} BOWLERS'), format_type)
            all_rounders_df = clean_data(pd.read_excel(xls, sheet_name=f'{format_type} ALL ROUNDERS'), format_type)

            batsmen_df['Role'] = 'Batsman'
            bowlers_df['Role'] = 'Bowler'
            all_rounders_df['Role'] = 'All-Rounder'

            df = pd.concat([batsmen_df, bowlers_df, all_rounders_df], ignore_index=True).fillna(0)

            df['Impact_Score'] = (
                df['Runs'] * 0.3 + df['Average'] * 0.2 + df['Strike_Rate'] * 0.1 +
                df['Wickets'] * 0.25 + (1 / (df['Economy'] + 1e-6)) * 0.15 +
                df['Centuries'] * 0.1 + df['Fifties'] * 0.05 + df['Notouts'] * 0.05
            )

            le = LabelEncoder()
            df['Role_Encoded'] = le.fit_transform(df['Role'])

            features = ['Role_Encoded', 'Runs', 'Average', 'Strike_Rate', 'Wickets', 'Economy', 'Centuries', 'Fifties', 'Matches', 'High_Score', 'Notouts', 'Balls_Faced', '4s', '6s', 'Ducks']
            for f in features:
                if f not in df.columns:
                    df[f] = 0

            X = df[features]
            y = df['Impact_Score']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42)
            model.fit(X_train, y_train)
            models[format_type] = (model, df)

            print(f"{format_type} model trained successfully!")
        except Exception as e:
            print(f"Error processing {format_type}: {str(e)}")

    if root.winfo_exists():
        root.after(0, lambda: [progress.stop(), progress.place_forget(), messagebox.showinfo("Success", "Model trained successfully!")])

def train_model_with_spinner():
    if not root.winfo_exists():
        return
    progress = ttk.Progressbar(root, mode="indeterminate", style="TProgressbar")
    progress.place(relx=0.5, rely=0.5, anchor="center")
    progress.start()
    threading.Thread(target=train_model, args=(root, progress), daemon=True).start()

def draw_gradient(canvas, width, height):
    canvas.delete("gradient")
    for i in range(height):
        # Convert colors to integers first before calculation
        bg_r = int(BG_COLOR[1:3], 16)
        bg_g = int(BG_COLOR[3:5], 16)
        bg_b = int(BG_COLOR[5:7], 16)
        
        sec_r = int(SECONDARY_COLOR[1:3], 16)
        sec_g = int(SECONDARY_COLOR[3:5], 16)
        sec_b = int(SECONDARY_COLOR[5:7], 16)
        
        # Calculate gradient colors
        r = int(bg_r + (sec_r - bg_r) * (i/height))
        g = int(bg_g + (sec_g - bg_g) * (i/height))
        b = int(bg_b + (sec_b - bg_b) * (i/height))
        
        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, width, i, fill=color, tags="gradient")

def create_particles(canvas):
    particles = []
    for _ in range(20):
        x = random.randint(0, root.winfo_screenwidth())
        y = random.randint(0, root.winfo_screenheight())
        particle = canvas.create_oval(x, y, x+5, y+5, fill=ACCENT_COLOR, tags="particle")
        particles.append(particle)
    animate_particles(canvas, particles)

def animate_particles(canvas, particles):
    try:
        for particle in particles:
            dx = random.uniform(-1, 1)
            dy = random.uniform(-1, 1)
            canvas.move(particle, dx, dy)
        canvas.after(50, animate_particles, canvas, particles)
    except tk.TclError:
        pass

def create_player_card(parent, player_name, role, stats, image, is_captain=False, is_wicketkeeper=False):
    card_bg = CARD_BG
    highlight_color = ACCENT_COLOR
    border_color = ACCENT_COLOR  # Default border color
    
    if is_captain:
        card_bg = CAPTAIN_COLOR
        highlight_color = "#ffd700"
        border_color = "#ff0000"  # Red border for captain
    elif is_wicketkeeper:
        card_bg = WK_COLOR
        highlight_color = "#00ffaa"
    
    # Card dimensions
    card = tk.Frame(parent, bg=card_bg, relief="ridge", bd=2, 
                    highlightbackground=border_color,
                    highlightthickness=2, width=1, height=160)  # Start with width=1 for flip effect
    card.pack_propagate(False)
    card.pack(side="left", padx=8, pady=5)

    card_canvas = tk.Canvas(card, bg=card_bg, highlightthickness=0)
    card_canvas.pack(fill="both", expand=True)
    card_canvas.create_rectangle(0, 0, 150, 160, fill=card_bg, outline="")

    if image:
        img_resized = image.resize((70, 70), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        image_label = tk.Label(card_canvas, image=photo, bg=card_bg)
        image_label.image = photo
        image_label.place(relx=0.5, rely=0.3, anchor="center")

    name_suffix = " (C)" if is_captain else " (WK)" if is_wicketkeeper else ""
    name_label = tk.Label(card_canvas, text=f"{player_name}{name_suffix}", 
                         font=("Montserrat", 9, "bold"),
                         fg=highlight_color, 
                         bg=card_bg,
                         wraplength=140)
    name_label.place(relx=0.5, rely=0.62, anchor="center")

    role_label = tk.Label(card_canvas, text=f"Role: {role}", 
                         font=("Montserrat", 8),
                         fg=TEXT_COLOR, bg=card_bg)
    role_label.place(relx=0.5, rely=0.75, anchor="center")

    # Role-specific stats with proper Economy display
    if role == "Batsman":
        stats_text = f"Runs: {stats['Runs']}\nAvg: {stats.get('Average', '-')}"
    elif role == "Bowler":
        economy = stats.get('Economy', 0)
        if isinstance(economy, (int, float)):
            economy = f"{economy:.2f}"
        stats_text = f"Wkts: {stats['Wickets']}\nEcon: {economy}"
    else:  # All-Rounder
        stats_text = f"Runs: {stats['Runs']}\nWkts: {stats['Wickets']}"

    stats_label = tk.Label(card_canvas, text=stats_text, 
                          font=("Montserrat", 7),
                          justify="center",
                          fg=TEXT_COLOR, bg=card_bg)
    stats_label.place(relx=0.5, rely=0.9, anchor="center")

    # 3D Flip Animation Logic
    def flip_3d(step=0):
        try:
            if step <= 20:
                if step < 10:
                    # Shrink width to simulate flip (front to edge)
                    width = int(150 * (1 - step / 10))
                    card.config(width=max(1, width))
                    card_canvas.config(width=max(1, width))
                    # Hide content during the "edge" phase
                    card_canvas.delete("all")
                    card_canvas.create_rectangle(0, 0, max(1, width), 160, fill=card_bg, outline="")
                else:
                    # Expand width to simulate flip (edge to back)
                    width = int(150 * ((step - 10) / 10))
                    card.config(width=width)
                    card_canvas.config(width=width)
                    card_canvas.delete("all")
                    card_canvas.create_rectangle(0, 0, width, 160, fill=card_bg, outline="")
                    # Restore content as card widens
                    if width > 50:  # Show content when wide enough
                        image_label.place(relx=0.5, rely=0.3, anchor="center")
                        name_label.place(relx=0.5, rely=0.62, anchor="center")
                        role_label.place(relx=0.5, rely=0.75, anchor="center")
                        stats_label.place(relx=0.5, rely=0.9, anchor="center")
                parent.update()
                parent.after(20, flip_3d, step + 1)
            else:
                # Ensure final state is correct
                card.config(width=150)
                card_canvas.config(width=150)
                card_canvas.delete("all")
                card_canvas.create_rectangle(0, 0, 150, 160, fill=card_bg, outline="")
                image_label.place(relx=0.5, rely=0.3, anchor="center")
                name_label.place(relx=0.5, rely=0.62, anchor="center")
                role_label.place(relx=0.5, rely=0.75, anchor="center")
                stats_label.place(relx=0.5, rely=0.9, anchor="center")
                card.pack(side="left", padx=8, pady=5)
        except tk.TclError:
            pass

    # Start with hidden content and trigger flip animation
    card_canvas.delete("all")
    card_canvas.create_rectangle(0, 0, 1, 160, fill=card_bg, outline="")
    image_label.place_forget()
    name_label.place_forget()
    role_label.place_forget()
    stats_label.place_forget()
    flip_3d()

    return card

def save_team_to_image(window, format_type):
    try:
        # Update the window to ensure all elements are properly rendered
        window.update()
        
        # Get the window dimensions including borders and title bar
        x = window.winfo_rootx()
        y = window.winfo_rooty()
        width = window.winfo_width()
        height = window.winfo_height()
        
        # Add additional pixels to capture the entire window
        extra_width = 20  # Account for window borders
        extra_height = 40  # Account for title bar
        
        # Capture the image with slightly larger dimensions
        image = ImageGrab.grab(bbox=(
            x - extra_width//2, 
            y - extra_height//2, 
            x + width + extra_width//2, 
            y + height + extra_height//2
        ))
        
        image_file = f"{format_type}_team_selection.png"
        image.save(image_file)
        messagebox.showinfo("Success", f"Team saved as {image_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save image: {str(e)}")

def create_gradient_button(parent, text, command):
    btn = tk.Canvas(parent, width=200, height=50, highlightthickness=0)
    btn.bind("<Button-1>", lambda e: (play_sound(), command()))
    btn.bind("<Enter>", lambda e: btn.config(cursor="hand2"))
    btn.bind("<Leave>", lambda e: btn.config(cursor=""))
    
    # Convert colors to integers first
    btn_r = int(BUTTON_COLOR[1:3], 16)
    btn_g = int(BUTTON_COLOR[3:5], 16)
    btn_b = int(BUTTON_COLOR[5:7], 16)
    
    hover_r = int(HOVER_COLOR[1:3], 16)
    hover_g = int(HOVER_COLOR[3:5], 16)
    hover_b = int(HOVER_COLOR[5:7], 16)
    
    # Draw initial gradient
    for i in range(50):
        r = int(btn_r + (hover_r - btn_r) * (i/50))
        g = int(btn_g + (hover_g - btn_g) * (i/50))
        b = int(btn_b + (hover_b - btn_b) * (i/50))
        color = f"#{r:02x}{g:02x}{b:02x}"
        btn.create_line(0, i, 200, i, fill=color)
    
    # Add text
    btn.create_text(100, 25, text=text, font=("Montserrat", 12, "bold"), fill=TEXT_COLOR)
    
    # Add hover effect
    def on_enter(e):
        for i in range(50):
            r = min(255, hover_r + 10)
            g = min(255, hover_g + 10)
            b = min(255, hover_b + 10)
            color = f"#{r:02x}{g:02x}{b:02x}"
            btn.create_line(0, i, 200, i, fill=color, tags="hover")
        btn.create_text(100, 25, text=text, font=("Montserrat", 12, "bold"), fill=TEXT_COLOR, tags="text")
    
    def on_leave(e):
        btn.delete("hover")
        for i in range(50):
            r = int(btn_r + (hover_r - btn_r) * (i/50))
            g = int(btn_g + (hover_g - btn_g) * (i/50))
            b = int(btn_b + (hover_b - btn_b) * (i/50))
            color = f"#{r:02x}{g:02x}{b:02x}"
            btn.create_line(0, i, 200, i, fill=color)
        btn.create_text(100, 25, text=text, font=("Montserrat", 12, "bold"), fill=TEXT_COLOR)
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn

def open_selection_window(format_type):
    if not models:
        messagebox.showwarning("Model Not Trained", "Please train the model first.")
        return

    new_window = tk.Toplevel(root)
    new_window.title(f"{format_type} Team Selection")
    new_window.geometry("1400x900")
    new_window.configure(bg=BG_COLOR)

    main_frame = tk.Frame(new_window, bg=BG_COLOR)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    best_11_frame = tk.Frame(main_frame, bg=BG_COLOR)
    best_11_frame.pack(pady=20)

    label = tk.Label(best_11_frame, text=f"Best 11 Players for {format_type}", 
                    font=("Montserrat", 24, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
    label.pack()

    best_11_row1 = tk.Frame(best_11_frame, bg=BG_COLOR)
    best_11_row1.pack()
    best_11_row2 = tk.Frame(best_11_frame, bg=BG_COLOR)
    best_11_row2.pack(pady=10)

    if format_type in models:
        model, df = models[format_type]
        df['Selection_Score'] = model.predict(df[['Role_Encoded', 'Runs', 'Average', 'Strike_Rate', 'Wickets', 'Economy', 'Centuries', 'Fifties', 'Matches', 'High_Score', 'Notouts', 'Balls_Faced', '4s', '6s', 'Ducks']])
        df = df.sort_values(by='Selection_Score', ascending=False)

        batsmen = df[df['Role'] == 'Batsman'].head(5)
        all_rounders = df[df['Role'] == 'All-Rounder'].head(3)
        bowlers = df[df['Role'] == 'Bowler'].head(3)
        best_11 = pd.concat([batsmen, all_rounders, bowlers]).drop_duplicates().head(11)

        if 'Keeper' in df.columns and not best_11[best_11['Keeper'] == 'Y'].empty:
            wicketkeeper = best_11[best_11['Keeper'] == 'Y'].iloc[0]
        elif 'Keeper' in df.columns and not df[df['Keeper'] == 'Y'].empty:
            wicketkeeper = df[df['Keeper'] == 'Y'].head(1).iloc[0]
            best_11 = pd.concat([best_11.head(10), pd.DataFrame([wicketkeeper])]).drop_duplicates().head(11)
        else:
            messagebox.showwarning("Warning", "No wicketkeeper found in the dataset!")
            wicketkeeper = None

        captain_index = best_11['Selection_Score'].idxmax()
        captain_name = best_11.loc[captain_index, 'Player']

        for i, (_, row) in enumerate(best_11.iterrows()):
            player_name = row['Player']
            role = row['Role']
            stats = {
                'Runs': row['Runs'],
                'Wickets': row['Wickets'],
                'Average': row['Average'],
                'Economy': row['Economy']  # Ensure economy is included
            }
            image = fetch_player_image(player_name)
            is_captain = (player_name == captain_name)
            is_wicketkeeper = (wicketkeeper is not None and player_name == wicketkeeper['Player'])
            if i < 8:
                create_player_card(best_11_row1, player_name, role, stats, image, is_captain, is_wicketkeeper)
            else:
                create_player_card(best_11_row2, player_name, role, stats, image, is_captain, is_wicketkeeper)

        substitutes_frame = tk.Frame(main_frame, bg=BG_COLOR)
        substitutes_frame.pack(pady=20)

        substitutes_label = tk.Label(substitutes_frame, text="Substitutes:", 
                                   font=("Montserrat", 18, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
        substitutes_label.pack()

        substitutes_row = tk.Frame(substitutes_frame, bg=BG_COLOR)
        substitutes_row.pack()

        substitutes = df[~df.index.isin(best_11.index)]
        substitute_batsmen = substitutes[substitutes['Role'] == 'Batsman'].head(2)
        substitute_bowlers = substitutes[substitutes['Role'] == 'Bowler'].head(2)
        substitute_all_rounders = substitutes[substitutes['Role'] == 'All-Rounder'].head(1)
        substitute_wicketkeeper = substitutes[substitutes['Keeper'] == 'Y'].head(1) if 'Keeper' in substitutes.columns else substitutes.head(1)
        substitute_spinner = substitutes[substitutes['Spinner'] == 'Y'].head(1) if 'Spinner' in substitutes.columns else substitutes.head(1)
        substitutes = pd.concat([substitute_batsmen, substitute_bowlers, substitute_all_rounders, substitute_wicketkeeper, substitute_spinner]).drop_duplicates()

        for _, row in substitutes.iterrows():
            player_name = row['Player']
            role = row['Role']
            stats = {
                'Runs': row['Runs'],
                'Wickets': row['Wickets'],
                'Average': row['Average'],
                'Economy': row['Economy']  # Ensure economy is included
            }
            image = fetch_player_image(player_name)
            is_wicketkeeper = ('Keeper' in row and row['Keeper'] == 'Y')
            create_player_card(substitutes_row, player_name, role, stats, image, is_captain=False, is_wicketkeeper=is_wicketkeeper)

        button_frame = tk.Frame(main_frame, bg=BG_COLOR)
        button_frame.pack(pady=20)

        stats_button = create_gradient_button(button_frame, "Show Player Stats", 
                                            lambda: show_player_stats(format_type, df))
        stats_button.pack(side="left", padx=10)

        image_button = create_gradient_button(button_frame, "Save Team as Image", 
                                            lambda: save_team_to_image(new_window, format_type))
        image_button.pack(side="left", padx=10)

    new_window.protocol("WM_DELETE_WINDOW", lambda: new_window.destroy())

def animate_widget(widget, anim_type, window):
    if anim_type == "fade_in":
        def fade_step(i=0):
            try:
                if not window.winfo_exists():
                    return
                alpha = i / 100
                widget.config(fg=f"#{int(int(ACCENT_COLOR[1:3], 16) * alpha):02x}{int(int(ACCENT_COLOR[3:5], 16) * alpha):02x}{int(int(ACCENT_COLOR[5:7], 16) * alpha):02x}")
                window.update()
                if i < 100:
                    window.after(20, fade_step, i + 5)
            except tk.TclError:
                pass
        if window.winfo_exists():
            fade_step()

def show_player_stats(format_type, df):
    stats_window = tk.Toplevel(root)
    stats_window.title(f"{format_type} Player Stats Dashboard")
    stats_window.geometry("1200x1800")
    stats_window.configure(bg=BG_COLOR)

    canvas = tk.Canvas(stats_window, bg=BG_COLOR, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    draw_gradient(canvas, 1000, 1800)

    label = tk.Label(canvas, text=f"{format_type} Player Stats Dashboard", 
                     font=("Montserrat", 20, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
    label.place(relx=0.5, rely=0.02, anchor="center")
    animate_widget(label, "fade_in", stats_window)

    player_list = df['Player'].tolist()
    player_var = tk.StringVar(value=player_list[0])
    player_dropdown = ttk.Combobox(canvas, textvariable=player_var, values=player_list, 
                                   font=("Montserrat", 12), width=30)
    player_dropdown.place(relx=0.5, rely=0.06, anchor="center")

    def plot_dashboard():
        selected_player = player_var.get()
        player_data = df[df['Player'] == selected_player]

        if player_data.empty:
            messagebox.showerror("Error", f"No data found for player: {selected_player}")
            return

        player_image = fetch_player_image(selected_player)
        if player_image:
            photo = ImageTk.PhotoImage(player_image)
            image_label = tk.Label(canvas, image=photo, bg=BG_COLOR)
            image_label.image = photo
            image_label.place(relx=0.5, rely=0.15, anchor="center")

        fig = sp.make_subplots(
            rows=6, cols=1,
            subplot_titles=("3D Performance (Runs, Wickets, Strike Rate)", 
                            "Impact Score Comparison",
                            "Runs Over Matches", 
                            "Average vs Strike Rate",
                            "Radar Chart: Player Profile", 
                            "Performance Heatmap"),
            specs=[[{"type": "scatter3d"}],
                   [{"type": "bar"}],
                   [{"type": "xy"}],
                   [{"type": "xy"}],
                   [{"type": "scatterpolar"}],
                   [{"type": "heatmap"}]],
            row_heights=[0.25, 0.15, 0.15, 0.15, 0.15, 0.15],
            vertical_spacing=0.08
        )

        fig.add_trace(go.Scatter3d(
            x=df['Runs'], y=df['Wickets'], z=df['Strike_Rate'],
            mode='markers', name='All Players',
            marker=dict(size=4, color='#1f77b4', opacity=0.6),
            text=df['Player'], hoverinfo="text+x+y+z"
        ), row=1, col=1)
        fig.add_trace(go.Scatter3d(
            x=player_data['Runs'], y=player_data['Wickets'], z=player_data['Strike_Rate'],
            mode='markers', name=selected_player,
            marker=dict(size=10, color='#ff4500', opacity=1),
            text=[selected_player], hoverinfo="text+x+y+z"
        ), row=1, col=1)
        fig.update_scenes(
            xaxis_title="Runs", yaxis_title="Wickets", zaxis_title="Strike Rate",
            bgcolor="#121212", camera_eye=dict(x=1.5, y=1.5, z=0.8),
            row=1, col=1
        )

        top_players = df.nlargest(10, 'Impact_Score')
        colors = ['#4682b4'] * 10
        if selected_player in top_players['Player'].values:
            colors[list(top_players['Player']).index(selected_player)] = '#ff4500'
        else:
            top_players = pd.concat([top_players.head(9), player_data]).drop_duplicates()
            colors = ['#4682b4'] * 9 + ['#ff4500']
        fig.add_trace(go.Bar(
            x=top_players['Player'], y=top_players['Impact_Score'],
            marker_color=colors, name='Impact Score',
            text=[f"{x:.1f}" for x in top_players['Impact_Score']],
            textposition='auto', hovertemplate="%{x}: %{y:.2f}"
        ), row=2, col=1)
        fig.update_yaxes(title_text="Impact Score", row=2, col=1)

        fig.add_trace(go.Scatter(
            x=df['Matches'].head(10), y=df['Runs'].head(10),
            mode='lines+markers', name='All Players',
            line=dict(color='#2ecc71', width=2), marker=dict(size=8)
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=player_data['Matches'], y=player_data['Runs'],
            mode='lines+markers', name=selected_player,
            line=dict(color='#e74c3c', width=3), marker=dict(size=12)
        ), row=3, col=1)
        fig.update_xaxes(title_text="Matches", row=3, col=1)
        fig.update_yaxes(title_text="Runs", row=3, col=1)

        fig.add_trace(go.Scatter(
            x=df['Average'].head(10), y=df['Strike_Rate'].head(10),
            mode='markers', name='All Players',
            marker=dict(size=10, color='#9b59b6', opacity=0.7)
        ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=player_data['Average'], y=player_data['Strike_Rate'],
            mode='markers', name=selected_player,
            marker=dict(size=14, color='#f1c40f', opacity=1)
        ), row=4, col=1)
        fig.update_xaxes(title_text="Average", row=4, col=1)
        fig.update_yaxes(title_text="Strike Rate", row=4, col=1)

        metrics = ['Runs', 'Wickets', 'Average', 'Strike_Rate', 'Economy']
        player_values = [player_data[m].iloc[0] / df[m].max() * 100 for m in metrics]
        fig.add_trace(go.Scatterpolar(
            r=player_values + [player_values[0]],
            theta=metrics + [metrics[0]],
            fill='toself', name=selected_player,
            line=dict(color='#ff4500'), fillcolor='rgba(255, 69, 0, 0.3)',
            hovertemplate="%{theta}: %{r:.1f}"
        ), row=5, col=1)
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
                angularaxis=dict(tickfont=dict(size=10)),
                bgcolor="#1A1A1A"
            )
        )

        corr_matrix = df[metrics].corr()
        fig.add_trace(go.Heatmap(
            z=corr_matrix.values, x=metrics, y=metrics,
            colorscale='RdYlBu', zmin=-1, zmax=1,
            text=[[f"{val:.2f}" for val in row] for row in corr_matrix.values],
            hoverinfo="text", texttemplate="%{text}",
            showscale=True
        ), row=6, col=1)

        fig.update_layout(
            title_text=f"Performance Dashboard for {selected_player}",
            title_x=0.5, title_font=dict(size=24, color="#FFD700"),
            height=1700, width=1200,
            showlegend=True,
            plot_bgcolor="#121212", paper_bgcolor="#121212",
            font=dict(color="#E0E0E0", size=12),
            margin=dict(l=80, r=80, t=150, b=100),
            legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5)
        )

        for row in [2, 3, 4]:
            fig.update_xaxes(showgrid=True, gridcolor="#333333", row=row, col=1)
            fig.update_yaxes(showgrid=True, gridcolor="#333333", row=row, col=1)

        html_file = f"{selected_player}_dashboard.html"
        pyo.plot(fig, filename=html_file, auto_open=True)

    plot_button = create_gradient_button(canvas, "Generate Dashboard", plot_dashboard)
    plot_button.place(relx=0.5, rely=0.9, anchor="center")

def typewriter_effect(label, text, index=0):
    try:
        if index < len(text) and label.winfo_exists():
            label.config(text=text[:index+1])
            root.after(100, typewriter_effect, label, text, index + 1)
    except tk.TclError:
        pass

def start_main_page():
    global root, canvas, title_label, tagline_label, logo_label, buttons_frame
    
    if 'root' in globals() and isinstance(root, tk.Tk):
        try:
            root.destroy()
        except:
            pass
    
    root = tk.Tk()
    root.title("Cricket Team Selector")
    root.geometry("1600x1000")
    root.configure(bg=BG_COLOR)
    
    # Proper window closing handler
    def on_closing():
        try:
            pygame.mixer.music.stop()
        except:
            pass
        root.destroy()
        root.quit()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.attributes("-alpha", 0.0)

    def fade_in_window(window, alpha=0.0):
        try:
            alpha += 0.05
            if alpha <= 1.0 and window.winfo_exists():
                window.attributes("-alpha", alpha)
                window.after(30, fade_in_window, window, alpha)
            else:
                window.attributes("-alpha", 1.0)
        except tk.TclError:
            pass

    def slide_in_frame(frame, y_pos=-1000):
        try:
            if y_pos < 0 and frame.winfo_exists():
                frame.place(relx=0.5, rely=0.5, anchor="center", y=y_pos)
                y_pos += 50
                frame.after(20, slide_in_frame, frame, y_pos)
            else:
                frame.place(relx=0.5, rely=0.5, anchor="center", y=0)
        except tk.TclError:
            pass

    content_frame = tk.Frame(root, bg=BG_COLOR)
    content_frame.place(relx=0.5, rely=0.5, anchor="center", width=1400, height=900, y=-1000)

    canvas = tk.Canvas(content_frame, bg=BG_COLOR, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    draw_gradient(canvas, 1600, 900)
    root.bind("<Configure>", lambda e: draw_gradient(canvas, content_frame.winfo_width(), content_frame.winfo_height()) if canvas.winfo_exists() else None)

    create_particles(canvas)

    title_label = tk.Label(canvas, text="Cricket-Verse", font=("Montserrat", 35, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
    title_label.place(relx=0.5, rely=0.09, anchor="center")
    animate_widget(title_label, "fade_in", root)

    tagline_label = tk.Label(canvas, text="", font=("Montserrat", 18), fg=ACCENT_COLOR, bg=BG_COLOR)
    tagline_label.place(relx=0.5, rely=0.15, anchor="center")
    typewriter_effect(tagline_label, "Unleash the Ultimate XI")

    try:
        logo = Image.open("PnP_logo.jpg")
        logo = logo.resize((300, 300), Image.Resampling.LANCZOS)
        logo_image = ImageTk.PhotoImage(logo)
        logo_label = tk.Label(canvas, image=logo_image, bg=BG_COLOR)
        logo_label.image = logo_image
        logo_label.place(relx=0.5, rely=0.35, anchor="center")
    except Exception as e:
        print(f"Error loading logo: {e}")

    buttons_frame = tk.Frame(canvas, bg=BG_COLOR, width=400, height=400)
    buttons_frame.place(relx=0.5, rely=0.65, anchor="center")

    train_btn = create_gradient_button(buttons_frame, "Train Model", train_model_with_spinner)
    train_btn.grid(row=0, column=0, padx=20, pady=10)

    odi_btn = create_gradient_button(buttons_frame, "Select ODI Team", lambda: open_selection_window("ODI"))
    odi_btn.grid(row=1, column=0, padx=20, pady=10)

    test_btn = create_gradient_button(buttons_frame, "Select TEST Team", lambda: open_selection_window("TEST"))
    test_btn.grid(row=2, column=0, padx=20, pady=10)

    t20_btn = create_gradient_button(buttons_frame, "Select T20 Team", lambda: open_selection_window("T20"))
    t20_btn.grid(row=3, column=0, padx=20, pady=10)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TProgressbar", troughcolor=BG_COLOR, background=BUTTON_COLOR, bordercolor=BUTTON_COLOR)

    fade_in_window(root)
    slide_in_frame(content_frame)

    play_background_music()
    root.mainloop()

if __name__ == "__main__":
    start_main_page()