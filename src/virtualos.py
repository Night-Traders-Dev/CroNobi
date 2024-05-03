import sys
import time
import datetime
import asyncio
from virtualfs import VirtualFileSystem
from virtualfs import Directory
from vcommands import VCommands
from virtualmachine import VirtualMachine
from virtualmachine import Wallet
from virtualkernel import VirtualKernel
from virtualkernel import UserAccount
from virtualkernel import PasswordFile
from virtualkernel import QShellInterpreter
from virtualkernel import VirtualProcess
from virtualkernel import Animations
from virtualinput import TerminalInput

class VirtualOS:
    def __init__(self):
        self.kernel = VirtualKernel()
        self.animations = Animations()
        self.wallet = Wallet("P3:b6c375b7be", "100000")
        self.vproc = VirtualProcess("Kernel", 0)
        self.passwordtools = PasswordFile("passwd")
        self.qshell = QShellInterpreter()
        self.kernel.log_command("Kernel Loaded...")
        self.kernel.get_checksum_file()
        self.kernel.compare_checksums()
        VCommands.clear_screen()
        self.kernel.log_command("Booting up VirtualOS...")
        self.kernel.log_command("Component Version Numbers:\n")
        self.kernel.print_component_versions(False)
        self.kernel.log_command(f"Python Version: {sys.version}")
        self.kernel.log_command("Initializing VirtualFileSystem...")
        self.fs = VirtualFileSystem()  # Initialize the filesystem
        self.kernel.create_process("filesystemd")
        self.kernel.log_command("VirtualFileSystem Loaded...")
        self.animations.boot_animation_rich()
        self.passwordtools.check_passwd_file(self.fs)
        self.active_user = self.passwordtools.online_user()
        self.user_dir = "/home/" + self.active_user
        self.user_perms = "rwxr-xr-x"
        self.su = False
        self.kernel.log_command("Default user permissions set(rwxr-xr-x)...")
        self.history = []
#        my_directory = Directory("/")
#        snapstamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#        snapshot_name = f"snapshot_{snapstamp}"
#        snapshot = my_directory.create_snapshot(self.fs, self.fs.current_directory, "/usr", snapshot_name)
#        self.kernel.log_command(f"Snapshot Created: {snapshot_name}")




        # Check if 'home' directory exists
        if "home" in self.fs.root.subdirectories:
            # Check if 'user' directory exists
            if self.active_user in self.fs.root.subdirectories["home"].subdirectories:
                # Set default starting directory to /home/user
                self.current_directory = self.fs.root.subdirectories["home"].subdirectories[self.active_user]
            else:
                self.kernel.log_command("User directory not found. Creating...")
                self.fs.create_directory(self.user_dir)
                self.current_directory = self.fs.root.subdirectories["home"].subdirectories[self.active_user]
        else:
            self.kernel.log_command("Home directory not found. Creating...")
            self.fs.create_directory("/home")
            self.fs.create_directory(self.user_dir)
            self.current_directory = self.fs.root.subdirectories["home"].subdirectories[self.active_user]

        self.kernel.log_command("Initializing VirtualMachine...")
        self.vm = VirtualMachine(self.kernel, self.fs)  # Create a VirtualMachine instance
        self.kernel.log_command(f"Permissions: {self.current_directory.permissions}")

        try:
            self.kernel.boot_verbose()
            self.kernel.log_command(f"Current directory: {self.current_directory.get_full_path()}")
        except Exception as e:
            self.kernel.log_command(f"Error during kernel boot: {str(e)}")

    def su_check(self, command):
            if not self.su:
                print(f"{command} requires su permission")
                self.kernel.log_command(f"[!!]su_check: {self.active_user} invalid permissions for {command}")
                return False
            else:
                return True

    def draw_vui(self):
        self.stdscr = curses.initscr()
        curses.curs_set(0)  # Hide the cursor
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Border color
        executed_commands = []
        while True:
            try:
                self.stdscr.clear()

                # Get current time
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Draw borders
                self.stdscr.border()

                # Print time in top right corner
                self.stdscr.addstr(0, curses.COLS - len(current_time) - 1, current_time)

                # Print vOS title in top left corner
                self.stdscr.addstr(0, 1, "vOS")

                # Display executed commands
                executed_commands_window = curses.newwin(curses.LINES - 6, curses.COLS - 4, 2, 2)
                for i, cmd in enumerate(executed_commands):
                    executed_commands_window.addstr(i, 0, cmd)

                # Get user input
                self.stdscr.addstr(curses.LINES - 4, 1, self.current_directory.get_full_path() + " $ ")
                command = self.stdscr.getstr(curses.LINES - 4, len(self.current_directory.get_full_path()) + 3).decode()

            except KeyboardInterrupt:
                self.stdscr.clear()
                VCommands.clear_screen()
                curses.curs_set(1)  # Hide the cursor
                break

            except Exception as e:
                self.kernel.handle_error(e)

            finally:
                curses.endwin()


    def run_shell(self):
        # List to store executed commands
        while True:
            try:

                command = input(f"{self.current_directory.get_full_path()} $ ").strip()
                self.history.append(command)
                self.kernel.log_command(command)  # Log the command
                if command == "exit" or command == "shutdown":
                    print("Shutting Down VirtualOS...")
                    self.vproc.shutdown_vproc(self)
                    self.fs.save_file_system("file_system.json")  # Save filesystem
                    self.kernel.delete_dmesg()  # Delete dmesg file on exit
                    self.animations.shutdown_animation()
                    break
                elif command.startswith("su"):
                    auth = self.passwordtools.su_prompt()
                    if auth:
                        parts = command.split(" ", 1)
                        permissions = parts[1] if len(parts) > 1 else "rwxrwxrwx"
                        VCommands.su(self, self.fs, self.current_directory, permissions)

                elif command.startswith("history"):
                    if not self.history:
                        print("Command history is empty.")
                        return

                    print("Command history:")
                    for i, command in enumerate(reversed(self.history), start=1):
                        print(f"{i}: {command}")

                elif command.startswith("reboot"):
                    confirmation = input("Are you sure you want to reboot? (yes/no): ").strip().lower()
                    if confirmation == "yes":
                        self.kernel.reboot_os()  # Call the reboot function from the kernel
                    else:
                        print("Reboot cancelled.")
                        self.kernel.log_command(f"[!]Reboot cancelled")

                elif command.startswith("perms"):
                    _, path = command.split(" ", 1)
                    VCommands.perms(self.fs, path)

                elif command.startswith("mkdir"):
                    _, path = command.split(" ", 1)
                    VCommands.mkdir(self.fs, self.current_directory, path)
                    self.fs.save_file_system("file_system.json")  # Save filesystem

                elif command.startswith("sysmon"):
                    self.vproc.monitor_processes(self)

                elif command.startswith("diff"):
                    _, path1, path2 = command.split(" ", 2)
                    VCommands.diff(self, self.fs, self.current_directory, path1, path2)

                elif command.startswith("cmp"):
                    _, path1, path2 = command.split(" ", 2)
                    VCommands.CMP(self.fs, self.current_directory, path1, path2)


                elif command.startswith("qshell"):
                    _, path = command.split(" ", 1)
                    filepath = self.current_directory.get_full_path() + "/" + path
                    self.kernel.log_command(f"qshell: {filepath}")
                    if self.fs.file_exists(filepath):
                        qshell_commands = self.qshell.execute_script(path)
                        for qshell_command in qshell_commands:
                            if qshell_command:
                                # Execute the parsed qShell command using the appropriate method from vcommands
                                self.execute_vcommand(qshell_command)
                    else:
                        print(f"{path} not found")
                elif command.startswith("ls"):
                    parts = command.split(" ")
                    if len(parts) > 1:
                        _, path = parts
                    else:
                        path = None
                    self.kernel.log_command(f"ls debug: {self.current_directory} and {path}")
                    VCommands.ls(self.fs, self.current_directory, path)

                elif command.startswith("cd"):
                    _, path = command.split(" ", 1)
                    self.current_directory = VCommands.cd(self, self.fs, self.current_directory, path)

                elif command.startswith("cat"):
                    try:
                        _, path = command.split(" ", 1)
                    except ValueError:
                        # If no path is specified, use the current directory
                        path = None
                    VCommands.cat(self.fs, self.current_directory, path)

                elif command.startswith("rmdir"):
                    _, path = command.split(" ", 1)
                    VCommands.rmdir(self.fs, self.current_directory, path)

                elif command.startswith("nano"):
                    try:
                        _, path = command.split(" ", 1)
                    except ValueError:
                        # If no path is specified, use the current directory
                        path = None
                    VCommands.nano(self, self.fs, self.current_directory, path)

                elif command.startswith("version"):
                    VCommands.version(self)

                elif command == "clear":
                    VCommands.clear_screen()

                elif command == "run_vm":  # Command to run the virtual machine
                    self.vm.run()

                elif command == "dmesg":  # Command to print virtual dmesg
                    if self.su_check(command):
                        self.kernel.print_dmesg()

                elif command == "uptime":
                    uptime = self.kernel.get_uptime()
                    print(f"vOS uptime: {uptime}")


                elif command == "update": 
                    if self.su_check(command):
                        self.kernel.update_vos()

                elif command == "reset_fs":
                    if self.su_check(command):
                        self.fs.reset_fs()

                elif command == "toggle_fs_monitoring":  # Command to toggle filesystem monitoring
                    self.kernel.toggle_filesystem_monitoring()

                elif command == "monitor_fs":  # Command to monitor filesystem
                    self.kernel.monitor_filesystem("file_system.json")

                elif command == "pwd":  # Corrected call to pwd method
                    VCommands.pwd(self.current_directory)  # Pass the current directory

                elif command.startswith("snapshot"):
                    VCommands.snapshot(self, self.fs)

                elif command.startswith("touch"):
                    try:
                        _, path = command.split(" ", 1)
                    except ValueError:
                        # If no path is specified, use the current directory
                        path = None
                    VCommands.touch(self.fs, self.current_directory, path)

                elif command.startswith("rm"):
                    _, path = command.split(" ", 1)
                    VCommands.rm(self.fs, self.current_directory, path)

                elif command.startswith("mv"):
                    _, old_path, new_path = command.split(" ", 2)
                    VCommands.mv(self.fs, self.current_directory, old_path, new_path)

                elif command.startswith("cp"):
                    _, src_path, dest_path = command.split(" ", 2)
                    VCommands.cp(self.fs, self.current_directory, src_path, dest_path)

                elif command.startswith("echo"):
                    parts = command.split(" ")
                    args = parts[1:-1]  # Extract arguments
                    file = parts[-1]  # Extract filename
                    self.kernel.log_command(f"Parts: {parts} Args: {args} File: {file}")
                    if ">>" not in command and ">" not in command:
                        file = None
                        args = parts[1:]
                    VCommands.echo(self.fs, self.current_directory, *args, file=file)

                elif command.startswith("logout"):
                    self.passwordtools.logout()

                elif command.startswith("adduser"):
                    if self.su_check(command):
                         _, username, password = command.split(" ", 2)
                         self.passwordtools.add_user(self.fs, username, password)
                         path = "/home/" + username
                         VCommands.mkdir(self.fs, path)

                elif command.startswith("deluser"):
                    if self.su_check(command):
                         _, username = command.split(" ", 1)
                         self.passwordtools.delete_user(self.fs, username)

                elif command.startswith("updateuser"):
                    if self.su_check(command):
                        _, username, new_password = command.split(" ", 2)
                        self.passwdtools.update_user(self.fs, username, new_password)

                elif command.startswith("readuser"):
                    _, username = command.split(" ", 1)
                    self.passwdtools.read_user(self.fs, username)

                elif command.startswith("wallet"):
                    print("This command is not setup")
                    #self.wallet.view_wallet()

                elif command.startswith("help"):
                    parts = command.split(" ")
                    if len(parts) > 1:
                        _, command_name = parts
                        if hasattr(VCommands, command_name):
                            # Display command specific help
                            print(getattr(VCommands, command_name).__doc__)
                        else:
                            print(f"Command '{command_name}' not found.")
                    else:
                        # Display overall help
                        print("Available commands:")
                        for method_name in dir(VCommands):
                            method = getattr(VCommands, method_name)
                            if callable(method) and not method_name.startswith("__"):
                                print(method.__doc__)
                else:
                    print("Command not found. Type 'help' to see available commands.")
                    self.kernel.log_command(f"[!] Command '{command}' not found.")
            except KeyboardInterrupt:
                print("Shutting Down VirtualOS...")
                self.vproc.shutdown_vproc(self)
                self.fs.save_file_system("file_system.json")  # Save filesystem
                self.kernel.delete_dmesg()  # Delete dmesg file on exit
                sys.exit(0)
            except Exception as e:
                self.kernel.handle_error(e)


if __name__ == "__main__":
    virtual_os = VirtualOS()
    virtual_os.run_shell()