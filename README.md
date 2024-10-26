# Vault Unlocker Scripts

This repository contains two scripts, written in Python and Bash, designed to attempt unlocking an encrypted volume using a password dictionary. These scripts support a variety of unlocking methods, including `apfs`, `coreStorage`, `appleRAID`, and `image`, and allow for concurrent password testing.

## Table of Contents
1. Requirements
2. Usage
   - Python Script
   - Bash Script
3. Options
4. Examples
5. License

---

## Requirements
1. **Python**: Requires Python 3.x.
2. **Bash**: Compatible with Bash shell environments (e.g., macOS, Linux).
3. **Disk Utility Commands**: `diskutil` and `hdiutil` for macOS volume management.
4. **Optional**: Python packages like `argparse` for command-line parsing (included by default).

## Usage

### Python Script
The Python script (`VaultUnlocker.py`) uses multithreading to efficiently test passwords in batches. Run the script with necessary arguments to specify the volume, password dictionary, unlocking method, and other options.

**Run the Python Script**:
```bash
python VaultUnlocker.py -v <volume_name> -d <dictionary_file> [options]

### Bash Script
The Bash script (`vault_unlocker.sh`) is a straightforward solution for users who prefer a shell script approach. It iterates through passwords in the dictionary and attempts to unlock the specified volume.

**Run the Bash Script**:
```bash
./vault_unlocker.sh -v <volume_name> -d <dictionary_file> [options]
```

# Options

| Option  |  Description  | 
|---|---|
|-v |Volume name to unlock (required).|
|-d |Dictionary file containing possible passphrases (required).|   
|-p |Progress interval (default: 1000).|
|-s |Start from a specific line number in the dictionary file (default: 1).|
|-m |Method for unlocking: apfs (default), coreStorage, appleRAID, image.|
|-c |(Bash only) Print each password as it is tested|

# Examples

## Python Script Example

To attempt unlocking a volume called "MyEncryptedDrive" using a dictionary file ``passwords.txt`` with a batch size of 100:
```bash
python VaultUnlocker.py -v MyEncryptedDrive -d passwords.txt -b 100
```

## Bash Script Example

To attempt unlocking the same volume with verbose output enabled and testing from the 10th password in ``passwords.txt``:
```bash
./vault_unlocker.sh -v MyEncryptedDrive -d passwords.txt -V -s 10
```

# License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
