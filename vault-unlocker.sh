#!/bin/bash

# Default values
PROGRESS_INTERVAL=1000
VERBOSE=false
PRINT_CURRENT=false
START_INDEX=1
METHOD="apfs"

# Variable to keep track of the last attempted password and its index
last_attempt_password=""
last_attempt_index=0

# Function to display usage instructions
usage() {
    printf "\nUsage: $0 -v volume_name -d dictionary.txt [-p progress_interval] [-s start_index] [-m method] [-c] [-V] [-l] [-h]\n\n"
    printf "Options:\n"
    printf "  -v    Volume name to unlock\n"
    printf "  -d    Dictionary file containing possible passphrases\n"
    printf "  -p    Progress interval (default: 1000)\n"
    printf "  -s    Start from a specific line number in the dictionary file (default: 1)\n"
    printf "  -m    Method for unlocking: apfs (default), coreStorage, appleRAID, image\n"
    printf "  -c    Print each password as it is tested\n"
    printf "  -V    Enable verbose output\n"
    printf "  -l    List available volumes\n"
    printf "  -h    Display this help message\n\n"
}

# Function to list available volumes
list_volumes() {
    printf "\nListing available volumes...\n"
    diskutil list
    exit 0
}

# Trap Ctrl-C (SIGINT) to handle graceful shutdown and print last attempted password
trap ctrl_c INT

ctrl_c() {
    printf "\n\nCaught interrupt signal (Ctrl-C)\n"
    if [[ $last_attempt_index -gt 0 ]]; then
        printf "Last attempted password: '%s' (at index %d)\n" "$last_attempt_password" "$last_attempt_index"
    else
        printf "No passwords attempted yet.\n"
    fi
    exit 1
}

# Parse command-line arguments
while getopts ":v:d:p:s:m:cVlh" opt; do
    case $opt in
        v) VOLUME_NAME="$OPTARG" ;;
        d) DICTIONARY_FILE="$OPTARG" ;;
        p) PROGRESS_INTERVAL="$OPTARG" ;;
        s) START_INDEX="$OPTARG" ;;
        m) METHOD="$OPTARG" ;;
        c) PRINT_CURRENT=true ;;
        V) VERBOSE=true ;;
        l) list_volumes ;;
        h) usage; exit 0 ;;
        \?) printf "Invalid option: -$OPTARG\n"; usage; exit 1 ;;
        :) printf "Option -$OPTARG requires an argument.\n"; usage; exit 1 ;;
    esac
done

# Check if the required arguments are provided
if [[ -z $VOLUME_NAME ]]; then
    printf "\nMissing Volume Name!\n\n"
    usage
    exit 1
fi

if [[ -z $DICTIONARY_FILE ]]; then
    printf "\nMissing Dictionary File!\n\n"
    usage
    exit 1
fi

# Get the UUID of the volume
VOLUME_UUID=$(diskutil info "$VOLUME_NAME" | grep "Volume UUID" | awk '{print $3}')

if [[ -z $VOLUME_UUID ]]; then
    printf "\nCould not find volume with name: %s\n\n" "$VOLUME_NAME"
    exit 1
fi

# Count the total number of passwords in the dictionary file
total_attempts=$(wc -l < "$DICTIONARY_FILE")

# Print a message if a start index has been provided
if [[ $START_INDEX -gt 1 ]]; then
    printf "\nStarting password testing from line %d...\n" "$START_INDEX"
fi

# Initialize attempt counter
attempt=0
found_password=""

# Function to attempt unlocking the volume using different methods
try_unlock() {
    local password=$1
    local output

    case $METHOD in
        apfs)
            output=$(diskutil apfs unlockVolume "$VOLUME_UUID" -passphrase "$password" 2>&1)
            ;;
        coreStorage)
            output=$(diskutil coreStorage unlockVolume "$VOLUME_UUID" -passphrase "$password" 2>&1)
            ;;
        appleRAID)
            output=$(diskutil appleRAID unlockVolume "$VOLUME_UUID" -passphrase "$password" 2>&1)
            ;;
        image)
            output=$(hdiutil attach -passphrase "$password" "$VOLUME_NAME" 2>&1)
            ;;
        *)
            printf "\nInvalid method: %s\n" "$METHOD"
            exit 1
            ;;
    esac

    # Print the output for debugging purposes if verbose mode is enabled
    if [[ $VERBOSE == true ]]; then
        echo "$output"
    fi

    # Check if the output indicates success
    if [[ $output == *"successfully unlocked"* ]] || [[ $output == *"attached successfully"* ]]; then
        echo "$password"
    else
        echo ""
    fi
}

# Start processing passwords from the specified index
tail -n +$START_INDEX "$DICTIONARY_FILE" | while IFS= read -r line; do
    ((attempt++))
    last_attempt_index=$((attempt + START_INDEX - 1))
    last_attempt_password="$line"

    if [[ $((attempt % PROGRESS_INTERVAL)) -eq 0 ]]; then
        printf "Progress: Tested %d out of %d passwords...\n" "$last_attempt_index" "$total_attempts"
    fi

    if [[ $PRINT_CURRENT == true ]]; then
        printf "Testing password: %s\n" "$line"
    fi

    found_password=$(try_unlock "$line")
    
    if [[ -n $found_password ]]; then
        printf "\nThe correct password is: %s (at index %d)\n\n" "$line" "$last_attempt_index"
        exit 0
    fi

done

printf "\nNo valid password found in the list.\n\n"
exit 1
