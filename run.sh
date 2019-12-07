#!/bin/bash

ips=($(hostname -I))
obj_name=$((RANDOM % 10))
echo "Available network Interfaces:"
for ip in "${ips[@]}"
do
    echo -e "\t" $ip
done
ip_new=${ips[0]}
ip_old=${ips[1]}
first1=${ip_new%%.*}

if [ $first1 -eq 10 ]
then
	ip=${ips[0]}
else	
	ip=${ips[1]}
fi
sed -i "s|address:.*|address: ${ip}/24|" BACpypes.ini
sed -i "s|objectIdentifier:.*|objectIdentifier: ${obj_name}|" BACpypes.ini

echo "BACpypes Configuration:"
echo "---------------------------------"
cat BACpypes.ini
echo "---------------------------------"

echo "Running Application: python server.py"
python server.py
