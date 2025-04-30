import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import json
import subprocess
import hashlib
import logging
from main_page import start_main_page

# Configure logging
logging.basicConfig(filename="login.log", level=logging.INFO, format="%(asctime)s - %(message)s")
CREDENTIALS_FILE = "credentials.json"
REMEMBER_FILE = "remembered.json"

# Credential handling
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_credentials():
    try:
        with open(CREDENTIALS_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"coach": hash_password("123")}

def save_credentials():
    with open(CREDENTIALS_FILE, "w") as file:
        json.dump(credentials, file)

credentials = load_credentials()

def check_credentials():
    login_button.config(text="Signing In...", bg="#028090")
    root.update()
    username = entry_username.get().strip()
    password = entry_password.get().strip()
    
    if not username or not password:
        messagebox.showerror("Error", "Username and password cannot be empty.")
        login_button.config(text="Log In", bg="#00A896")
        return
    
    hashed_password = hash_password(password)
    if username in credentials and credentials[username] == hashed_password:
        logging.info(f"Successful login for {username}")
        if remember_var.get():
            with open(REMEMBER_FILE, "w") as file:
                json.dump({"username": username, "password": password}, file)
        messagebox.showinfo("Login Successful", "Welcome to the system!")
        # Fade out the login window
        def fade_out_window(window, alpha=1.0):
            alpha -= 0.05
            if alpha >= 0:
                window.attributes("-alpha", alpha)
                window.after(30, fade_out_window, window, alpha)
            else:
                window.attributes("-alpha", 0.0)
        fade_out_window(root)
        root.after(50, lambda: [root.destroy(), start_main_page()])  # Destroy login and start main page
    else:
        logging.warning(f"Failed login attempt for {username}")
        messagebox.showerror("Login Failed", "Invalid username or password.")
        shake_frame(frame)
        login_button.config(text="Log In", bg="#00A896")

def reset_fields():
    entry_username.delete(0, tk.END)
    entry_password.delete(0, tk.END)

# Shake animation for frame on login failure
def shake_frame(frame, count=4, direction=1):
    if count > 0:
        x_shift = 10 * direction
        frame.place(relx=0.5, rely=0.5, anchor="center", x=x_shift)
        frame.after(50, shake_frame, frame, count - 1, -direction)
    else:
        frame.place(relx=0.5, rely=0.5, anchor="center", x=0)

# Reset password window
def open_reset_password_page():
    reset_window = tk.Toplevel(root)
    reset_window.title("Reset Password")
    reset_window.geometry("500x450")
    reset_window.config(bg="#1A2526")
    reset_window.resizable(False, False)

    frame = tk.Frame(reset_window, bg="#2E3B3C", bd=2, relief="groove")
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    def reset_password():
        username = entry_reset_username.get().strip()
        new_password = entry_new_password.get().strip()
        confirm_password = entry_confirm_password.get().strip()
        if username not in credentials:
            messagebox.showerror("Error", "Username not found.", parent=reset_window)
        elif new_password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.", parent=reset_window)
        elif len(new_password) < 4:
            messagebox.showerror("Error", "Password must be at least 4 characters.", parent=reset_window)
        else:
            credentials[username] = hash_password(new_password)
            save_credentials()
            messagebox.showinfo("Success", "Password reset successfully!", parent=reset_window)
            reset_window.destroy()

    tk.Label(frame, text="Reset Password", font=("Helvetica", 20, "bold"), bg="#2E3B3C", fg="#FFFFFF").pack(pady=(20, 20))
    tk.Label(frame, text="Username", font=("Helvetica", 12), bg="#2E3B3C", fg="#A3BFFA").pack(pady=5)
    entry_reset_username = tk.Entry(frame, font=("Helvetica", 12), width=25, bg="#3C4B4C", fg="#FFFFFF", bd=0)
    entry_reset_username.pack(pady=5)
    tk.Label(frame, text="New Password", font=("Helvetica", 12), bg="#2E3B3C", fg="#A3BFFA").pack(pady=5)
    entry_new_password = tk.Entry(frame, font=("Helvetica", 12), width=25, bg="#3C4B4C", fg="#FFFFFF", bd=0, show="*")
    entry_new_password.pack(pady=5)
    tk.Label(frame, text="Confirm Password", font=("Helvetica", 12), bg="#2E3B3C", fg="#A3BFFA").pack(pady=5)
    entry_confirm_password = tk.Entry(frame, font=("Helvetica", 12), width=25, bg="#3C4B4C", fg="#FFFFFF", bd=0, show="*")
    entry_confirm_password.pack(pady=5)
    
    tk.Button(frame, text="Reset Password", font=("Helvetica", 12, "bold"), bg="#00A896", fg="#FFFFFF", 
              command=reset_password, bd=0, padx=20, pady=5).pack(pady=20)
    tk.Button(frame, text="Close", font=("Helvetica", 10), bg="#F94144", fg="#FFFFFF", 
              command=reset_window.destroy, bd=0, padx=10, pady=5).pack()

# Sign-up window
def open_signup_page():
    signup_window = tk.Toplevel(root)
    signup_window.title("Sign Up")
    signup_window.geometry("500x450")
    signup_window.config(bg="#1A2526")
    signup_window.resizable(False, False)

    frame = tk.Frame(signup_window, bg="#2E3B3C", bd=2, relief="groove")
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    def signup():
        username = entry_signup_username.get().strip()
        password = entry_signup_password.get().strip()
        if username in credentials:
            messagebox.showerror("Error", "Username already exists.", parent=signup_window)
        elif len(password) < 4:
            messagebox.showerror("Error", "Password must be at least 4 characters.", parent=signup_window)
        else:
            credentials[username] = hash_password(password)
            save_credentials()
            messagebox.showinfo("Success", "Account created successfully!", parent=signup_window)
            signup_window.destroy()

    tk.Label(frame, text="Sign Up", font=("Helvetica", 20, "bold"), bg="#2E3B3C", fg="#FFFFFF").pack(pady=(20, 20))
    tk.Label(frame, text="Username", font=("Helvetica", 12), bg="#2E3B3C", fg="#A3BFFA").pack(pady=5)
    entry_signup_username = tk.Entry(frame, font=("Helvetica", 12), width=25, bg="#3C4B4C", fg="#FFFFFF", bd=0)
    entry_signup_username.pack(pady=5)
    tk.Label(frame, text="Password", font=("Helvetica", 12), bg="#2E3B3C", fg="#A3BFFA").pack(pady=5)
    entry_signup_password = tk.Entry(frame, font=("Helvetica", 12), width=25, bg="#3C4B4C", fg="#FFFFFF", bd=0, show="*")
    entry_signup_password.pack(pady=5)
    
    tk.Button(frame, text="Create Account", font=("Helvetica", 12, "bold"), bg="#00A896", fg="#FFFFFF", 
              command=signup, bd=0, padx=20, pady=5).pack(pady=20)
    tk.Button(frame, text="Close", font=("Helvetica", 10), bg="#F94144", fg="#FFFFFF", 
              command=signup_window.destroy, bd=0, padx=10, pady=5).pack()

# Animations
def fade_in_window(window, alpha=0.0):
    alpha += 0.05
    if alpha <= 1.0:
        window.attributes("-alpha", alpha)
        window.after(30, fade_in_window, window, alpha)
    else:
        window.attributes("-alpha", 1.0)

def slide_in_frame(frame, x_pos=-500):
    if x_pos < 0:
        frame.place(relx=0.5, rely=0.5, anchor="center", x=x_pos)
        x_pos += 20
        frame.after(20, slide_in_frame, frame, x_pos)
    else:
        frame.place(relx=0.5, rely=0.5, anchor="center", x=0)


def bounce_title(label, y_pos=110, direction="down"):
    if direction == "down" and y_pos > 100:
        label.place(relx=0.5, y=y_pos, anchor="center")
        y_pos -= 2
        label.after(20, bounce_title, label, y_pos, "down")
    elif direction == "down" and y_pos <= 100:
        label.place(relx=0.5, y=y_pos, anchor="center")
        label.after(20, bounce_title, label, y_pos + 2, "up")
    elif direction == "up" and y_pos < 105:
        label.place(relx=0.5, y=y_pos, anchor="center")
        y_pos += 2
        label.after(20, bounce_title, label, y_pos, "up")
    else:
        label.place(relx=0.5, y=100, anchor="center")

def scale_entry(entry, width=0):
    if width < 25:
        entry.config(width=width)
        width += 1
        entry.after(25, scale_entry, entry, width)
    else:
        entry.config(width=25)

# Button hover effects
def on_enter_login(e):
    login_button.config(bg="#02C39A")

def on_leave_login(e):
    login_button.config(bg="#00A896")

def on_enter_reset(e):
    reset_button.config(bg="#F3722C")

def on_leave_reset(e):
    reset_button.config(bg="#F94144")

# Toggle password visibility
def toggle_password():
    if show_password_var.get():
        entry_password.config(show="")
    else:
        entry_password.config(show="*")

# Load remembered credentials
def load_remembered_credentials():
    try:
        with open(REMEMBER_FILE, "r") as file:
            data = json.load(file)
            entry_username.insert(0, data.get("username", ""))
            entry_password.insert(0, data.get("password", ""))
    except FileNotFoundError:
        pass

# Main window setup
root = tk.Tk()
root.title("Cricket-Verse")
root.state('zoomed')  # Full-screen mode
root.config(bg="#1A2526")
root.attributes("-alpha", 0.0)  # Start invisible for fade-in

# Canvas for background with dark overlay
canvas = tk.Canvas(root, bg="#1A2526", highlightthickness=0)
canvas.pack(fill="both", expand=True)

try:
    image_original = Image.open("cric_1.png")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    stretched_image = image_original.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
    background_image = ImageTk.PhotoImage(stretched_image)
    canvas.create_image(0, 0, image=background_image, anchor="nw")
    canvas.create_rectangle(0, 0, screen_width, screen_height, fill="#000000", stipple="gray50")
except Exception as e:
    print(f"Failed to load or stretch background image: {e}")

# Gradient frame simulation
frame = tk.Frame(canvas, bg="#2E3B3C", bd=2, relief="groove")
frame.place(relx=0.5, rely=0.5, anchor="center", width=500, height=550, x=-500)
gradient_canvas = tk.Canvas(frame, bg="#2E3B3C", highlightthickness=0)
gradient_canvas.place(x=0, y=0, width=500, height=550)
gradient_canvas.create_rectangle(0, 0, 500, 550, fill="#2E3B3C", outline="")
gradient_canvas.create_rectangle(0, 0, 500, 275, fill="#3C4B4C", outline="")  # Gradient top half

# Add rounded logo above "Welcome Back!"
try:
    logo_image = Image.open("PnP_logo.jpg")  # Replace "logo.png" with your logo file path
    logo_size = 55  # Increased from 50 to 100 for a bigger logo
    logo_image = logo_image.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # Create a circular mask
    mask = Image.new("L", (logo_size, logo_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, logo_size, logo_size), fill=255)
    
    # Apply the mask to make the logo circular
    logo_image = logo_image.convert("RGBA")
    logo_image.putalpha(mask)
    
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = tk.Label(frame, image=logo_photo, bg="#3C4B4C")
    logo_label.image = logo_photo  # Keep a reference to avoid garbage collection
    logo_label.place(relx=0.5, y=50, anchor="center")  # Adjusted from y=10 to y=50 to fit within frame
except Exception as e:
    print(f"Failed to load logo image: {e}")
    logo_label = tk.Label(frame, text="Logo", font=("Helvetica", 12), bg="#3C4B4C", fg="#FFFFFF")
    logo_label.place(relx=0.5, y=50, anchor="center")  # Fallback text if logo fails

# Title with bounce animation - Adjusted downward to accommodate larger logo
title_label = tk.Label(frame, text="Welcome Back!", font=("Helvetica", 24, "bold"), bg="#3C4B4C", fg="#FFFFFF")
title_label.place(relx=0.5, y=110, anchor="center")  # Moved from y=70 to y=110 to fit below larger logo

# Adjusted bounce_title function to match new position
def bounce_title(label, y_pos=110, direction="down"):  # Changed starting y_pos from 70 to 110
    if direction == "down" and y_pos > 100:  # Changed lower bound from 60 to 100
        label.place(relx=0.5, y=y_pos, anchor="center")
        y_pos -= 2
        label.after(20, bounce_title, label, y_pos, "down")
    elif direction == "down" and y_pos <= 100:
        label.place(relx=0.5, y=y_pos, anchor="center")
        label.after(20, bounce_title, label, y_pos + 2, "up")
    elif direction == "up" and y_pos < 105:  # Adjusted upper bound from 65 to 105
        label.place(relx=0.5, y=y_pos, anchor="center")
        y_pos += 2
        label.after(20, bounce_title, label, y_pos, "up")
    else:
        label.place(relx=0.5, y=100, anchor="center")  # Final resting position at y=100

subtitle_label = tk.Label(frame, text="Please Login or Signup to Continue", font=("Helvetica", 14), bg="#3C4B4C", fg="#A3BFFA")
subtitle_label.pack(pady=(140, 20), anchor="center")  # Adjusted pady from (100, 20) to (140, 20) to shift down

# Entry fields with icons
entry_frame = tk.Frame(frame, bg="#2E3B3C")
entry_frame.pack(pady=10)

# Username field with icon placeholder
username_frame = tk.Frame(entry_frame, bg="#2E3B3C")
username_frame.pack(pady=5)
tk.Label(username_frame, text="👤", font=("Helvetica", 14), bg="#2E3B3C", fg="#FFFFFF").pack(side="left", padx=5)
tk.Label(username_frame, text="Username", font=("Helvetica", 12), bg="#2E3B3C", fg="#FFFFFF").pack(side="left")
entry_username = tk.Entry(username_frame, font=("Helvetica", 14), width=0, bg="#3C4B4C", fg="#FFFFFF", bd=0, justify="center")
entry_username.pack(side="left", pady=5, padx=5)
scale_entry(entry_username)

# Password field with icon placeholder
password_frame = tk.Frame(entry_frame, bg="#2E3B3C")
password_frame.pack(pady=5)
tk.Label(password_frame, text="🔒", font=("Helvetica", 14), bg="#2E3B3C", fg="#FFFFFF").pack(side="left", padx=5)
tk.Label(password_frame, text="Password", font=("Helvetica", 12), bg="#2E3B3C", fg="#FFFFFF").pack(side="left")
entry_password = tk.Entry(password_frame, font=("Helvetica", 14), width=0, bg="#3C4B4C", fg="#FFFFFF", bd=0, show="*", justify="center")
entry_password.pack(side="left", pady=5, padx=5)
entry_password.bind("<Return>", lambda event: check_credentials())
scale_entry(entry_password)

# Checkbuttons in a sub-frame for proper placement
check_frame = tk.Frame(frame, bg="#2E3B3C")
check_frame.pack(pady=10)
show_password_var = tk.BooleanVar()
tk.Checkbutton(check_frame, text="Show Password", variable=show_password_var, command=toggle_password, 
               bg="#2E3B3C", fg="#A3BFFA", selectcolor="#2E3B3C", activebackground="#2E3B3C").pack(side="right", padx=20)
remember_var = tk.BooleanVar()
tk.Checkbutton(check_frame, text="Remember Me", variable=remember_var, bg="#2E3B3C", fg="#A3BFFA", 
               selectcolor="#2E3B3C", activebackground="#2E3B3C").pack(side="left", padx=20)

# Buttons with hover effects
login_button = tk.Button(frame, text="Log In", font=("Helvetica", 12, "bold"), bg="#00A896", fg="#FFFFFF", 
                         width=15, height=2, bd=0, command=check_credentials)
login_button.pack(pady=20)
login_button.bind("<Enter>", on_enter_login)
login_button.bind("<Leave>", on_leave_login)

reset_button = tk.Button(frame, text="Reset", font=("Helvetica", 12, "bold"), bg="#F94144", fg="#FFFFFF", 
                         width=15, height=2, bd=0, command=reset_fields)
reset_button.pack(pady=10)
reset_button.bind("<Enter>", on_enter_reset)
reset_button.bind("<Leave>", on_leave_reset)

# Links
forgot_label = tk.Label(frame, text="Forgot Password?", font=("Helvetica", 10, "underline"), bg="#2E3B3C", fg="#00A896", cursor="hand2")
forgot_label.place(relx=0.25, rely=0.95, anchor="center")
forgot_label.bind("<Button-1>", lambda e: open_reset_password_page())

signup_label = tk.Label(frame, text="Sign Up", font=("Helvetica", 10, "underline"), bg="#2E3B3C", fg="#00A896", cursor="hand2")
signup_label.place(relx=0.75, rely=0.95, anchor="center")
signup_label.bind("<Button-1>", lambda e: open_signup_page())

# Start animations
fade_in_window(root)
slide_in_frame(frame)
bounce_title(title_label)

load_remembered_credentials()
root.mainloop()