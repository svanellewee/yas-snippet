import subprocess
import os
import sys
import io
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

class UniversalAnnotator:
    def __init__(self):
        self.temp_path = "/tmp/snip_temp.png"
        self.img = None
        self.last_x, self.last_y = None, None
        self.history = []
        self.color = "red"
        self.line_width = 3

    def capture(self):
        """Triggers native capture tools for macOS or Sway."""
        if sys.platform == "darwin":
            # macOS: -i is interactive selection
            subprocess.run(["screencapture", "-i", self.temp_path])
        elif os.environ.get("SWAYSOCK") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
            try:
                # Sway: slurp for region, grim for capture
                selection = subprocess.check_output(["slurp"]).decode().strip()
                subprocess.run(["grim", "-g", selection, self.temp_path])
            except subprocess.CalledProcessError:
                return False
        else:
            print("Error: This script specifically targets macOS and Sway/Wayland.")
            return False
        
        if not os.path.exists(self.temp_path) or os.path.getsize(self.temp_path) == 0:
            return False
            
        self.img = Image.open(self.temp_path).convert("RGB")
        return True

    def show_ui(self):
        self.root = tk.Tk()
        self.root.title("Annotator")
        
        # --- THE FOCUS FIX ---
        self.root.attributes("-topmost", True)
        if sys.platform == "darwin":
            # Force macOS to treat the Python process as the active frontmost app
            os.system(f'''/usr/bin/osascript -e 'tell app "System Events" to set frontmost of every process whose unix id is {os.getpid()} to true' ''')
        self.root.focus_force()
        
        # UI Toolbar
        ctrl = tk.Frame(self.root, bg="#222")
        ctrl.pack(side="top", fill="x")
        
        tk.Button(ctrl, text="🎨 Color", command=self.change_color, bg="#444", fg="red").pack(side="left", padx=5, pady=5)
        tk.Button(ctrl, text="↩ Undo", command=self.undo, bg="#444", fg="red").pack(side="left", padx=5)
        tk.Button(ctrl, text="📋 Copy & Close", command=self.copy_to_clipboard, bg="#2ecc71", fg="red", font=('Arial', 10, 'bold')).pack(side="left", padx=10)
        tk.Button(ctrl, text="💾 Save File", command=self.save_to_file, bg="#444", fg="red").pack(side="left", padx=5)
        
        # Canvas Setup
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas = tk.Canvas(self.root, width=self.img.width, height=self.img.height, highlightthickness=0)
        self.canvas.pack()
        self.canvas_img_obj = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        
        self.draw = ImageDraw.Draw(self.img)
        
        # Mouse Bindings
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.paint_line)
        
        # Shortcut Bindings
        undo_key = "<Command-z>" if sys.platform == "darwin" else "<Control-z>"
        self.root.bind(undo_key, lambda e: self.undo())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Release topmost after focus is established so child dialogs work
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        
        self.root.mainloop()

    def start_draw(self, event):
        # Save state for undo
        self.history.append(self.img.copy())
        if len(self.history) > 40: self.history.pop(0)
        self.last_x, self.last_y = event.x, event.y

    def paint_line(self, event):
        if self.last_x and self.last_y:
            x, y = event.x, event.y
            # Canvas Preview
            self.canvas.create_line(self.last_x, self.last_y, x, y, 
                                   fill=self.color, width=self.line_width, capstyle=tk.ROUND, smooth=True)
            # Permanent Image Draw
            self.draw.line([self.last_x, self.last_y, x, y], fill=self.color, width=self.line_width)
            self.last_x, self.last_y = x, y

    def undo(self):
        if self.history:
            self.img = self.history.pop()
            self.draw = ImageDraw.Draw(self.img)
            self.tk_img = ImageTk.PhotoImage(self.img)
            self.canvas.itemconfig(self.canvas_img_obj, image=self.tk_img)

    def change_color(self):
        c = colorchooser.askcolor(title="Choose brush color")[1]
        if c: self.color = c

    def copy_to_clipboard(self):
        """Saves current state and pushes to system clipboard with correct MIME type."""
        self.img.save(self.temp_path)
        try:
            if sys.platform == "darwin":
                # macOS binary clipboard copy
                subprocess.run(['osascript', '-e', f'set the clipboard to (read (POSIX file "{self.temp_path}") as «class PNGf»)' ])
            else:
                # Wayland binary clipboard copy
                with open(self.temp_path, "rb") as f:
                    subprocess.run(['wl-copy', '-t', 'image/png'], input=f.read())
            
            self.root.destroy()
            print("Copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Clipboard failed: {e}")

    def save_to_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if path:
            self.img.save(path)
            self.root.destroy()

if __name__ == "__main__":
    app = UniversalAnnotator()
    if app.capture():
        app.show_ui()
