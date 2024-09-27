import subprocess
import threading
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

class VaultUnlocker:
    def __init__(self, volume=None, dictionary=None, start=1, progress_interval=1000, 
                 batch_size=100, method='apfs', workers=4, debug=False):
        """
        Initialize the VaultUnlocker class with parameters that can be used when called programmatically.
        """
        self.volume = volume
        self.dictionary = dictionary
        self.start = start
        self.progress_interval = progress_interval
        self.batch_size = batch_size
        self.method = method
        self.workers = workers
        self.debug = debug
        self.attempted_passwords = []
        self.last_attempt_password = ""
        self.last_attempt_index = 0
        self.stop_event = threading.Event()
        self.total_attempts = 0
        self.progress_queue = Queue()

    def try_unlock(self, volume_uuid, password, method):
        """
        Attempt to unlock the volume using the given password and method.
        """
        cmd_map = {
            "apfs": ["diskutil", "apfs", "unlockVolume", volume_uuid, "-passphrase", password],
            "coreStorage": ["diskutil", "coreStorage", "unlockVolume", volume_uuid, "-passphrase", password],
            "appleRAID": ["diskutil", "appleRAID", "unlockVolume", volume_uuid, "-passphrase", password],
            "image": ["hdiutil", "attach", "-passphrase", password, volume_uuid],
        }

        command = cmd_map[method]
        command_str = ' '.join(command)

        try:
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout + result.stderr
            return output, command_str
        except Exception as e:
            print(f"Error trying to unlock with command '{command_str}': {e}", flush=True)
            return "", command_str

    def test_passwords(self, volume_uuid, passwords, method, start_index):
        """
        Test a list of passwords to unlock the volume.
        """
        for index, password in enumerate(passwords):
            if self.stop_event.is_set():
                break

            current_index = start_index + index
            self.last_attempt_password = password
            self.attempted_passwords.append(password)
            self.last_attempt_index = current_index

            if self.debug:
                print(f"Testing password: {password} (at index {current_index})", flush=True)

            output, command_str = self.try_unlock(volume_uuid, password, method)

            # Check for success
            if self.debug:
                print(f"Command: {command_str}\nOutput: {output}", flush=True)
                
            if output and ("successfully unlocked" in output or "attached successfully" in output or "Unlocked" in output):
                print(f"\nThe correct password is: {password} (at index {current_index})\n", flush=True)
                self.stop_event.set()
                self.save_successful_password(password)
                break

            if output and "already unlocked" in output:
                print(f"\nThe volume {self.volume} is already unlocked.\n", flush=True)
                self.stop_event.set()
                break
            
            self.progress_queue.put(current_index)

    def save_successful_password(self, password):
        """
        Save the successful password to a file.
        """
        output_file = 'successful_password.txt'
        home_output_file = os.path.expanduser(f'~/successful_password_{self.volume}.txt')

        try:
            with open(output_file, 'w') as f:
                f.write(password)
            print(f"Password successfully written to {output_file}.", flush=True)
        except IOError:
            try:
                with open(home_output_file, 'w') as f:
                    f.write(password)
                print(f"Could not write to current directory. Password written to {home_output_file}.", flush=True)
            except IOError as e:
                print(f"Failed to write password to both locations. Error: {e}", flush=True)

    def print_progress(self):
        """
        Continuously print progress messages from the queue.
        """
        while not self.stop_event.is_set() or not self.progress_queue.empty():
            try:
                current_index = self.progress_queue.get(timeout=1)
                print(f"Progress: Tested {current_index} out of {self.total_attempts} passwords...", flush=True)
            except Exception:
                continue

    def signal_handler(self, sig, frame):
        """
        Handle the Ctrl+C interrupt signal.
        """
        print("\nCaught interrupt signal (Ctrl-C)", flush=True)
        if self.last_attempt_password:
            print(f"Last attempted password: {self.last_attempt_password} (at index {self.last_attempt_index})", flush=True)
        else:
            print("No passwords attempted yet.", flush=True)
        self.stop_event.set()
        sys.exit(0)

    def list_volumes(self):
        """
        List available volumes using diskutil.
        """
        print("\nListing available volumes...", flush=True)
        subprocess.run(["diskutil", "list"])

    def unlock(self):
        """
        The core logic to unlock the volume using the provided password dictionary.
        """
        if not self.volume or not self.dictionary:
            print("Volume and dictionary must be provided.", flush=True)
            return

        try:
            volume_info = subprocess.check_output(["diskutil", "info", self.volume]).decode()
            volume_uuid = volume_info.split("Volume UUID:")[1].strip().split()[0]
        except Exception as e:
            print(f"Could not find volume with name: {self.volume}. Error: {e}", flush=True)
            sys.exit(1)

        self.total_attempts = sum(1 for line in open(self.dictionary))

        if self.start > 1:
            print(f"\nStarting password testing from line {self.start}...\n", flush=True)

        with open(self.dictionary) as f:
            all_passwords = f.readlines()[self.start - 1:]

        progress_thread = threading.Thread(target=self.print_progress)
        progress_thread.start()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = []
            for i in range(0, len(all_passwords), self.batch_size):
                batch = [p.strip() for p in all_passwords[i:i + self.batch_size]]
                futures.append(executor.submit(self.test_passwords, volume_uuid, batch, self.method, self.start + i))

            for future in futures:
                future.result()

        if not self.stop_event.is_set():
            print(f"Tested all {self.total_attempts} passwords, but no valid password was found", flush=True)

        self.stop_event.set()
        progress_thread.join()


if __name__ == "__main__":
    import argparse
    import signal

    parser = argparse.ArgumentParser(description='Unlock a volume using a password dictionary.')
    parser.add_argument('-v', '--volume', required=True, help='Volume name to unlock')
    parser.add_argument('-d', '--dictionary', required=True, help='Dictionary file containing possible passphrases')
    parser.add_argument('-s', '--start', type=int, default=1, help='Start from a specific line number in the dictionary file (default: 1)')
    parser.add_argument('-p', '--progress', type=int, default=1000, help='Progress report interval (default: 1000)')
    parser.add_argument('-b', '--batch', type=int, default=100, help='Batch size for concurrent testing (default: 100)')
    parser.add_argument('-m', '--method', choices=['apfs', 'coreStorage', 'appleRAID', 'image'], default='apfs', help='Method for unlocking (default: apfs)')
    parser.add_argument('-w', '--workers', type=int, default=4, help='Maximum number of worker threads (default: 4)')
    parser.add_argument('-D', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-V', '--version', action='version', version='Vault Crack Script - Version 1.0', help='Show version information')

    args = parser.parse_args()

    unlocker = VaultUnlocker(
        volume=args.volume,
        dictionary=args.dictionary,
        start=args.start,
        progress_interval=args.progress,
        batch_size=args.batch,
        method=args.method,
        workers=args.workers,
        debug=args.debug
    )

    signal.signal(signal.SIGINT, unlocker.signal_handler)
    unlocker.unlock()
