import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import subprocess, os, shutil, ctypes, sys, tempfile, threading
from datetime import datetime

# --- Logging ---
LOG_FILE = os.path.join(tempfile.gettempdir(), "ITToolKit_Combined_Log.txt")

def log_action(message):
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def update_log_viewer(log_widget):
    try:
        with open(LOG_FILE, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = "No logs yet."
    log_widget.config(state=tk.NORMAL)
    log_widget.delete(1.0, tk.END)
    log_widget.insert(tk.END, content)
    log_widget.config(state=tk.DISABLED)
    log_widget.after(2000, lambda: update_log_viewer(log_widget))

# --- ITToolKit Tab ---
def create_ittoolkit_tab(tab):
    def run_command(command, log=True):
        try:
            subprocess.run(command, shell=True, check=True)
            if log:
                log_action(f"Executed: {command}")
        except subprocess.CalledProcessError as e:
            log_action(f"Error: {e}")
            messagebox.showerror("Error", f"Command failed:\n{e}")

    def flush_dns(): run_command("ipconfig /flushdns")
    def reset_winsock(): run_command("netsh winsock reset")
    def release_renew():
        if messagebox.askyesno("Warning", "Doing a release/renew will disconnect remote sessions. Proceed?"):
            run_command("ipconfig /release && ipconfig /renew")
    def force_gpupdate(): run_command("gpupdate /force")
    def battery_report(): run_command("powercfg /batteryreport")
    def enable_rdp():
        try:
            subprocess.run("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\" /v fDenyTSConnections /t REG_DWORD /d 0 /f", shell=True)
            subprocess.run('netsh advfirewall firewall set rule group="remote desktop" new enable=Yes', shell=True)
            messagebox.showinfo("RDP", "Remote Desktop enabled.")
            log_action("RDP enabled")
        except Exception as e:
            messagebox.showerror("RDP Error", str(e))
            log_action(f"RDP enable failed: {e}")
    def disable_rdp():
        try:
            subprocess.run("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\" /v fDenyTSConnections /t REG_DWORD /d 1 /f", shell=True)
            subprocess.run('netsh advfirewall firewall set rule group="remote desktop" new enable=No', shell=True)
            messagebox.showinfo("RDP", "Remote Desktop disabled.")
            log_action("RDP disabled")
        except Exception as e:
            messagebox.showerror("RDP Error", str(e))
            log_action(f"RDP disable failed: {e}")

    actions = [
        ("Flush DNS", flush_dns),
        ("Reset Winsock", reset_winsock),
        ("IP Release/Renew", release_renew),
        ("Force GPUpdate", force_gpupdate),
        ("Battery Report", battery_report),
        ("Enable RDP", enable_rdp),
        ("Disable RDP", disable_rdp)
    ]
    for txt, cmd in actions:
        tk.Button(tab, text=txt, command=cmd, bg="#3c3f41", fg="white", relief=tk.FLAT).pack(pady=4, fill='x')

# --- NetDig Tab ---
def create_netdig_tab(tab):
    def run_command(command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout if result.returncode == 0 else result.stderr
            log_action(f"Command: {command}\nOutput: {output}")
            if result.returncode != 0:
                raise Exception(output)
            messagebox.showinfo("Result", output)
        except Exception as e:
            log_action(f"Error running {command}: {e}")
            messagebox.showerror("Error", str(e))

    def prompt_user(msg): return simpledialog.askstring("Input", msg)

    actions = [
        ("User Domain Info", lambda: run_command(f'net user "{prompt_user("Enter username:")}" /domain')),
        ("Account Info", lambda: run_command(f'net user "{prompt_user("Enter username:")}"')),
        ("Change Password", lambda: run_command(f'net user "{prompt_user("Enter username:")}" "{simpledialog.askstring("Password", "Enter new password:", show="*")}"')),
        ("Force GPUpdate", lambda: run_command("gpupdate /force")),
        ("List All Users", lambda: run_command("net user"))
    ]
    for txt, cmd in actions:
        tk.Button(tab, text=txt, command=cmd, bg="#3c3f41", fg="white", relief=tk.FLAT).pack(pady=4, fill='x')

# --- WinImageFix Tab ---
def create_healthcheck_tab(tab):
    output = scrolledtext.ScrolledText(tab, height=15, bg="#2d2d2d", fg="white")
    output.pack(expand=True, fill='both')

    progress = ttk.Progressbar(tab, length=400, mode="determinate")
    progress.pack(pady=5)

    def log(msg):
        output.insert(tk.END, msg + "\n")
        output.see(tk.END)

    def run_commands():
        cmds = [
            "sfc /scannow",
            "dism /online /cleanup-image /scanhealth",
            "dism /online /cleanup-image /checkhealth",
            "dism /online /cleanup-image /restorehealth"
        ]
        progress['maximum'] = len(cmds)
        for i, cmd in enumerate(cmds, 1):
            log(f"[>] {cmd}")
            try:
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    log("    " + line.strip())
                proc.wait()
                log("[✓] Done" if proc.returncode == 0 else f"[✗] Exit code {proc.returncode}")
            except Exception as e:
                log(f"[!] Error: {e}")
            progress["value"] = i
        log_action("System health check completed")
        messagebox.showinfo("Complete", "All checks finished.")

    tk.Button(tab, text="Start Health Scan", command=lambda: threading.Thread(target=run_commands, daemon=True).start()).pack()

# --- DateTime Tab ---
def create_datetime_tab(tab):
    def set_date_time():
        try:
            new_date = simpledialog.askstring("Date", "Enter new date (MM-DD-YYYY):")
            new_time = simpledialog.askstring("Time", "Enter new time (HH:MM:SS):")
            if new_date:
                subprocess.run(["date", new_date], shell=True)
                log_action(f"Date set to {new_date}")
            if new_time:
                subprocess.run(["time", new_time], shell=True)
                log_action(f"Time set to {new_time}")
            messagebox.showinfo("DateTime Set", "Date and Time updated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            log_action(f"Date/Time update error: {e}")

    tk.Button(tab, text="Set Date and Time", command=set_date_time, bg="#3c3f41", fg="white", relief=tk.FLAT).pack(pady=20)

# --- Main GUI ---
def main():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        messagebox.showerror("Admin Required", "Please run this application as administrator.")
        sys.exit()

    root = tk.Tk()
    root.title("Chidiac's ITToolKit")
    root.geometry("600x700")
    root.configure(bg="#1e1e1e")

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    style = ttk.Style()
    style.theme_use('default')
    style.configure('.', background='#1e1e1e', foreground='white')

    tabs = {
        "Basic Fixes": create_ittoolkit_tab,
        "User Dig": create_netdig_tab,
        "Win Image Fix": create_healthcheck_tab,
        "Date Time Set": create_datetime_tab
    }

    for name, builder in tabs.items():
        frame = tk.Frame(notebook, bg="#1e1e1e")
        notebook.add(frame, text=name)
        builder(frame)

    log_label = tk.Label(root, text="Unified Log Viewer", bg="#1e1e1e", fg="white")
    log_label.pack(pady=2)

    log_viewer = scrolledtext.ScrolledText(root, height=10, bg="#2d2d2d", fg="white")
    log_viewer.pack(fill='both', expand=True, padx=10, pady=5)
    log_viewer.config(state=tk.DISABLED)
    update_log_viewer(log_viewer)

    root.mainloop()

if __name__ == "__main__":
    main()
