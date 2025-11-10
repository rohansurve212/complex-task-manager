#!/usr/bin/env bash

# Get the current date and time
now=$(date)

# Print a decorative line and log the start time of the script
echo "><O> ******************** ><O>"
echo "Start: $now"

# Log a message indicating the script is about to interact with LDAP
echo "><O> Go fish in LDAP ><O>"   

# Execute the Python script to interact with LDAP
python /gofish-ldap.py

# Get the current date and time again
now=$(date)

# Log the end time of the script
echo "End: $now"

# Print another decorative line to signify the script's end
echo "><O> -*-*-*-*-*-*-*-*-*-* ><O>"