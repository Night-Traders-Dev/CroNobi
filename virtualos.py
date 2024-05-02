import sys
import time
from virtualfs import VirtualFileSystem
from vcommands import VCommands
from virtualmachine import VirtualMachine
from virtualkernel import VirtualKernel
from virtualkernel import UserAccount
from virtualkernel import PasswordFile
from virtualkernel import QShellInterpreter
from virtualkernel import VirtualProcess

class VirtualOS:
    def __init__(self):
        self.kernel = VirtualKernel()
        self.vproc = VirtualProcess("vprocd")
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
        self.load_with_loading_circle()  # Call method to load with loading circle
        self.passwordtools.check_passwd_file(self.fs)
        self.active_user = self.passwordtools.online_user()
        self.user_dir = "/home/" + self.active_user
        self.user_perms = "rwxr-xr-x"
        self.su = False
        self.kernel.log_command("Default user permissions set(rwxr-xr-x)...")

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

    def load_with_loading_circle(self):
        self.kernel.log_command("Boot Animation Loaded...")
        loading_animation = ['|', '/', '-', '\\']  # ASCII characters for the loading animation
        for _ in range(10):  # Repeat the animation 10 times
            for char in loading_animation:
                sys.stdout.write('\r' + f"Booting vOS... {char}")  # Overwrite the same line with the loading animation
                sys.stdout.flush()
                time.sleep(0.1)  # Add a short delay to control the speed of the animation
        sys.stdout.write('\r')  # Clear the loading animation line
        sys.stdout.flush()
        self.kernel.log_command("File system loaded successfully.")

    def su_check(self, command):
            if not self.su:
                print(f"{command} requires su permission")
                self.kernel.log_command(f"[!!]su_check: {self.active_user} invalid permissions for {command}")
                return False
            else:
                return True


    def run_shell(self):
        while True:
            try:
                command = input(f"{self.current_directory.get_full_path()} $ ").strip()
                self.kernel.log_command(command)  # Log the command
                if command == "exit" or command == "shutdown":
                    print("Shutting Down VirtualOS...")
                    self.fs.save_file_system("file_system.json")  # Save filesystem
                    self.kernel.delete_dmesg()  # Delete dmesg file on exit
                    break
                elif command.startswith("su"):
                    auth = self.passwordtools.su_prompt()
                    if auth:
                        parts = command.split(" ", 1)
                        permissions = parts[1] if len(parts) > 1 else "rwxrwxrwx"
                        VCommands.su(self, self.fs, self.current_directory, permissions)

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
                    VCommands.mkdir(self.fs, path)
                    self.fs.save_file_system("file_system.json")  # Save filesystem

                elif command.startswith("sysmon"):
                    self.vproc.monitor_processes(self)

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
                    VCommands.rmdir(self.fs, path)
                    self.fs.save_file_system("file_system.json")  # Save filesystem

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
                    VCommands.mv(self.fs, old_path, new_path)

                elif command.startswith("cp"):
                    _, src_path, dest_path = command.split(" ", 2)
                    VCommands.cp(self.fs, src_path, dest_path)

                elif command.startswith("echo"):
                    _, *args = command.split(" ")
                    VCommands.echo(*args)

                elif command.startswith("logout"):
                    self.passwordtools.logout()

                elif command.startswith("adduser"):
                    if self.su_check(command):
                         _, username, password = command.split(" ", 2)
                         self.passwordtools.add_user(self.fs, username, password)
                         path = "/home/" + username
                         VCommands.mkdir(self.fs, path)
                         self.fs.save_file_system("file_system.json")  # Save filesystem

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
            except Exception as e:
                self.kernel.handle_error(e)

if __name__ == "__main__":
    virtual_os = VirtualOS()
    virtual_os.run_shell()
