# ==== Imports ====
import threading  # For running tasks asynchronously
import ttkbootstrap as tb  # Modern themed widgets for Tkinter
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from tkinter import messagebox, ttk  # Standard UI components
import tkinter as tk  # Core Tkinter module for GUI
import google.generativeai as genai  # Gemini AI integration
import re  # Regular expressions for parsing
from fpdf import FPDF  # PDF generation library
from fpdf.enums import XPos, YPos
import os  # For OS-specific tasks
import platform  # To detect the current OS

# ==== Gemini AI Configuration ====
genai.configure(api_key="PASTE YOUR API KEY HERE")
client = genai.GenerativeModel(model_name="gemini-1.5-flash")

# ==== Flags for state control ====
is_fetching = False  # To avoid multiple roadmap requests at the same time
cancel_fetch = False  # Allows user to cancel generation mid-way


# ==== Function to Fetch Roadmap from Gemini AI ====
def fetch_roadmap(topic, duration, level, loading_popup, progress_bar):
    global is_fetching, cancel_fetch
    try:
        # Prompt for Gemini to generate a structured roadmap
        prompt = (
            f"Give me a complete roadmap to learn {topic} in {duration} days. "
            f"Assume user level: {level}. Format:\n Day 1: Tasks\n Day 2: ...\n"
            f"Also provide sources. No extra formatting."
        )

        # Send prompt to Gemini
        response = client.generate_content(prompt)

        # Check and extract response
        if response and hasattr(response, "text"):
            roadmap = response.text
            print("Raw roadmap:", roadmap)

            if cancel_fetch:
                loading_popup.destroy()
                messagebox.showinfo("Cancelled", "Roadmap generation was cancelled.")
                return

            loading_popup.destroy()
            show_roadmap_popup(roadmap)  # Display the roadmap
        else:
            loading_popup.destroy()
            messagebox.showerror("Error", "Failed to get a valid response from the API.")
    except Exception as e:
        loading_popup.destroy()
        messagebox.showerror("Error", f"Failed to generate roadmap: {str(e)}")
    finally:
        is_fetching = False


# ==== Function to Parse Raw Roadmap Text ====
def parse_roadmap(raw_text):
    roadmap_data = {}
    lines = raw_text.strip().split('\n')
    current_day = None

    print("--- Parsing with 'Day X:' format ---")
    for i, line in enumerate(lines):
        line = line.strip()
        print(f"Line {i+1}: '{line}'")

        # Match "Day X: content"
        day_match = re.match(r"Day (\d+):(.*)", line)
        if day_match:
            day_num = day_match.group(1)
            content = day_match.group(2).strip()
            current_day = f"Day {day_num}"
            roadmap_data[current_day] = {"tasks": content, "sources": []}
            print(f"  -> Found Day: {current_day}, Content: '{content}'")
            continue

        # Look for "Source: " in following lines
        if current_day and line.startswith("Source:"):
            sources_str = line.split("Source:", 1)[1].strip()
            sources = [s.strip() for s in sources_str.split(',') if s.strip()]
            roadmap_data[current_day]["sources"].extend(sources)
            print(f"  -> Found Sources: {sources} for {current_day}")
            continue

        # If just continuation of tasks
        elif current_day and line:
            roadmap_data[current_day]["tasks"] += "\n" + line
            print(f"  -> Appending to tasks for {current_day}: '{line}'")

    print("--- Parsing Finished ---")
    print("Parsed roadmap_data:", roadmap_data)
    return roadmap_data


# ==== Function to Generate and Save PDF ====
def generate_pdf(roadmap_text):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        lines = roadmap_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Bold font for "Day" headings
                if line.startswith("Day"):
                    pdf.set_font("Helvetica", style="B", size=12)
                else:
                    pdf.set_font("Helvetica", size=12)
                pdf.multi_cell(0, 10, line.encode('latin-1', 'ignore').decode('latin-1'),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        filename = "roadmap.pdf"
        pdf.output(filename)
        messagebox.showinfo("Success", f"Roadmap saved as {filename}")
    except Exception as e:
        messagebox.showerror("PDF Error", f"Failed to save PDF: {str(e)}")


# ==== Function to Open PDF using Default Viewer ====
def open_pdf():
    filename = "roadmap.pdf"
    if os.path.exists(filename):
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
            elif platform.system() == "Darwin":
                os.system(f"open {filename}")
            else:  # Linux
                os.system(f"xdg-open {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")
    else:
        messagebox.showwarning("File Not Found", "No PDF file has been generated yet.")


# ==== Function to Show the Roadmap in a Popup ====
def show_roadmap_popup(roadmap):
    result_popup = tk.Toplevel(app)
    result_popup.title("📘 Your Roadmap")
    result_popup.geometry("800x600")
    result_popup.transient(app)

    # Parse and prepare data
    roadmap_data = parse_roadmap(roadmap)

    # Create scrollable text area
    text_widget = tk.Text(result_popup, wrap="word", font=("Helvetica", 11), bg="#2b2b2b", fg="white", padx=10, pady=10)
    text_widget.pack(fill="both", expand=True)
    scrollbar = ttk.Scrollbar(result_popup, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Populate roadmap content
    if not roadmap_data:
        text_widget.insert("1.0", "No roadmap data available.")
    else:
        for day, data in roadmap_data.items():
            text_widget.insert("end", f"\n{day}: ", "heading")
            for task in data["tasks"].strip().split('\n'):
                text_widget.insert("end", f"{task}\n", "normal")
            for source in data["sources"]:
                text_widget.insert("end", f"  - {source}\n", "source")

    # Styling tags
    text_widget.tag_configure("heading", font=("Helvetica", 12, "bold"), foreground="lightblue")
    text_widget.tag_configure("normal", font=("Helvetica", 11))
    text_widget.tag_configure("source", font=("Helvetica", 11, "italic"), foreground="gray")

    # Button controls
    button_frame = ttk.Frame(result_popup)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text="Save as PDF", command=lambda: generate_pdf(roadmap)).pack(side="left", padx=5)
    ttk.Button(button_frame, text="Open PDF", command=open_pdf).pack(side="left", padx=5)
    ttk.Button(button_frame, text="Close", command=result_popup.destroy).pack(side="left", padx=5)


# ==== Function to Start Roadmap Generation ====
def generate_roadmap():
    global is_fetching, cancel_fetch
    topic = topic_entry.get().strip()
    duration = duration_entry.get().strip()
    level = level_choice.get()

    # Validate inputs
    if not topic or not duration or not level:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    try:
        duration = int(duration)
        if duration <= 0:
            raise ValueError
    except ValueError:
        messagebox.showwarning("Input Error", "Duration must be a valid number of days.")
        return

    if is_fetching:
        messagebox.showwarning("Busy", "Please wait, a roadmap is already being generated.")
        return

    is_fetching = True
    cancel_fetch = False

    # Show loading popup with spinner
    loading_popup = tk.Toplevel(app)
    loading_popup.title("Please Wait")
    loading_popup.geometry("350x150")
    loading_popup.transient(app)
    loading_popup.grab_set()

    ttk.Label(loading_popup, text="⏳ Generating roadmap...", font=("Helvetica", 12)).pack(pady=10)
    progress_bar = ttk.Progressbar(loading_popup, mode="indeterminate", length=200)
    progress_bar.pack(pady=10)
    progress_bar.start()

    # Cancel button inside popup
    def cancel_operation():
        global cancel_fetch
        cancel_fetch = True
        loading_popup.destroy()
        is_fetching = False
        messagebox.showinfo("Cancelled", "Roadmap generation cancelled.")

    ttk.Button(loading_popup, text="Cancel", command=cancel_operation).pack(pady=10)

    # Launch roadmap generation in background thread
    threading.Thread(
        target=fetch_roadmap,
        args=(topic, duration, level, loading_popup, progress_bar),
        daemon=True
    ).start()


# ==== GUI Setup ====
app = tb.Window(themename="darkly")
app.title("🚀 Python Roadmap Generator")
app.geometry("600x450")
app.resizable(False, False)

main_frame = ttk.Frame(app)
main_frame.pack(padx=20, pady=20, fill="both", expand=True)

# ==== UI Components ====
ttk.Label(main_frame, text="🎯 Roadmap Generator", font=("Helvetica", 20, "bold")).pack(pady=10)

ttk.Label(main_frame, text="📘 What do you want to learn?", font=("Helvetica", 12)).pack(pady=5)
topic_entry = ttk.Entry(main_frame, width=40, font=("Helvetica", 11))
topic_entry.pack(pady=5)
ToolTip(topic_entry, "Enter the topic you want to learn (e.g., Python, Machine Learning)")

ttk.Label(main_frame, text="⏳ Time you have (days)", font=("Helvetica", 12)).pack(pady=5)
duration_entry = ttk.Entry(main_frame, width=40, font=("Helvetica", 11))
duration_entry.pack(pady=5)
ToolTip(duration_entry, "Enter the number of days (e.g., 30)")

ttk.Label(main_frame, text="⭐ Your current level", font=("Helvetica", 12)).pack(pady=5)
level_choice = ttk.Combobox(main_frame, values=["Beginner", "Intermediate", "Advanced"], font=("Helvetica", 11))
level_choice.set("Beginner")
level_choice.pack(pady=5)

ttk.Button(main_frame, text="⚡ Generate Roadmap", style="success.TButton", command=generate_roadmap).pack(pady=20)

# Start the application loop
app.mainloop()
