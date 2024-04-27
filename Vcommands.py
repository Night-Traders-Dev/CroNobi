import os
import sys
import platform
from virtualfs import File

class VCommands:
    @staticmethod
    def help(command=None):
        """
        help: Display help information\nUsage: help [command]
        If no command is provided, displays overall help information.
        If a command is provided, displays specific help information for that command.
        """
        if command:
            if hasattr(VCommands, command):
                method = getattr(VCommands, command)
                print(method.__doc__ or "No help available for this command.")
            else:
                print(f"Command '{command}' not found.")
        else:
            print("Available commands:")
            print("mkdir - Create a directory")
            print("ls - List files and directories")
            print("cd - Change directory")
            print("cat - Display file content")
            print("rmdir - Remove a directory")
            print("nano - Open a file in a nano-like text editor")
            print("version - Show version information")
            print("clear - Clear the screen")
            print("pwd - Print the current directory")
            print("touch - Create a new file")
            print("rm - Remove a file")
            print("mv - Move a file or directory")
            print("cp - Copy a file or directory")
            print("echo - Display arguments")

    @staticmethod
    def mkdir(fs, path=None):
        """
        mkdir: Create a directory\nUsage: mkdir [directory_path]
        If no directory path is provided, creates a directory in the current directory.
        """
        if not path:
            print("Error: Please specify a directory path to create.")
            return
        # Concatenate current directory and path
        directory_path = os.path.join(fs.current_directory.get_full_path(), path) if not path.startswith('/') else path
        fs.create_directory(directory_path)
        fs.kernel.log_command(f"Created directory: {directory_path}")

    @staticmethod
    def ls(fs, current_directory, path=None):
        """
        ls: List files and directories\nUsage: ls [directory_path]
        If no directory path is provided, lists the contents of the current directory.
        """
        if not path:
            directory = current_directory
        else:
            try:
                directory = fs.find_directory(current_directory, path)
            except FileNotFoundError:
                print(f"Directory '{path}' not found.")
                return

        for name, item in directory.subdirectories.items():
            print(f"{name}/")
        for name, item in directory.files.items():
            print(name)

    @staticmethod
    def cd(fs, current_directory, path):
        """
        cd: Change directory\nUsage: cd [directory_path]
        """
        if not path or path == ".":
            return current_directory
        elif path == "..":
            if current_directory == fs.root:
                print("Already at the top of the directory.")
            else:
                return current_directory.parent                                                                                                                      else:
            try:
                new_directory = fs.find_directory(current_directory, path)
                return new_directory
            except FileNotFoundError:
                print(f"Directory '{path}' not found.")
                return current_directory

    @staticmethod
    def cat(fs, path=None):
        """
        cat: Display file content\nUsage: cat [file_path]
        """
        if not path:
            print("Error: Please specify a file path to read.")
            return
        try:
            file_content = fs.read_file(path)
            print(file_content)
        except FileNotFoundError:
            print(f"File '{path}' not found.")

    @staticmethod
    def rmdir(fs, path=None):
        """
        rmdir: Remove a directory\nUsage: rmdir [directory_path]
        """
        if not path:
            print("Error: Please specify a directory path to remove.")
            return
        try:
            fs.remove_directory(path)
            fs.kernel.log_command(f"Removed directory: {path}")
        except FileNotFoundError:
            print(f"Directory '{path}' not found.")

    @staticmethod
    def nano(fs, current_directory, path=None):
        """
        nano: Open a file in a nano-like text editor\nUsage: nano [file_path]
        If no file path is provided, prompts the user to enter a file name and creates a new file.
        """
        if not path:
            filename = input("Enter filename: ")
            if not filename.strip():
                print("Filename cannot be empty.")
                return
            path = os.path.join(current_directory.get_full_path(), filename)
        print("Nano-like text editor. Press :w to save and exit.")
        nano_file = ""
        while True:
            line = input()
            if line == ":w":
                fs.create_file(path, nano_file)
                break
            nano_file += line + "\n"

    @staticmethod
    def version():
        """
        version: Show version information
        """
        print("VOS Version: V0.0.1")
        print(f"Python Version: {sys.version}")
        print("VirtualFS Version: V0.0.1")
        print("VirtualMachine Version: V0.0.1")

    @staticmethod
    def clear_screen():
        """
        clear: Clear the screen
        """
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")

    @staticmethod
    def pwd(current_directory):
        """
        pwd: Print the current directory
        """
        print(current_directory.get_full_path())

    @staticmethod
    def touch(fs, path=None):
        """
        touch: Create a new file\nUsage: touch [file_path]
        If no file path is provided, creates a file in the current directory.
        """
        if not path:
            print("Error: Please specify a file path to create.")
            return
        # Concatenate current directory and path
        file_path = os.path.join(fs.current_directory.get_full_path(), path) if not path.startswith('/') else path

        parent_directory_path, filename = os.path.split(file_path)
        parent_directory = fs.find_directory(fs.root, parent_directory_path)
        parent_directory.add_file(File(filename))
        fs.kernel.log_command(f"Created file: {file_path}")

    @staticmethod
    def rm(fs, path=None):
        """
        rm: Remove a file\nUsage: rm [file_path]
        """
        if not path:
            print("Error: Please specify a file path to remove.")
            return

        try:
            fs.remove_file(path)
            fs.kernel.log_command(f"Removed file: {path}")
        except FileNotFoundError:
            print(f"File '{path}' not found.")

    @staticmethod
    def mv(fs, old_path, new_path):
        """
        mv: Move a file or directory\nUsage: mv [old_path] [new_path]
        """
        try:
            fs.rename_file(old_path, new_path)
            fs.kernel.log_command(f"Moved file '{old_path}' to '{new_path}'")
        except FileNotFoundError:
            print(f"File '{old_path}' not found.")
        except FileExistsError:
            print(f"File '{new_path}' already exists.")

    @staticmethod
    def cp(fs, src_path, dest_path):
        """
        cp: Copy a file or directory\nUsage: cp [source_path] [destination_path]
        """
        try:
            file_content = fs.read_file(src_path)
            fs.create_file(dest_path, file_content)
            fs.kernel.log_command(f"Copied file '{src_path}' to '{dest_path}'")
        except FileNotFoundError:
            print(f"File '{src_path}' not found.")

    @staticmethod
    def echo(*args):
        """
        echo: Display arguments\nUsage: echo [arguments...]
        """
        print(" ".join(args))