#!/bin/bash

./setup_newrelic.sh $NEW_RELIC_API_KEY

if [ -z $ENVIRONMENT ]; 
then 
export SETTINGS=local; 
export CONFIG=Local; 
else
export SETTINGS=$ENVIRONMENT;
export CONFIG=${ENVIRONMENT^};
fi;

if [ -z $ROOT_PASSWORD ]; then ROOT_PASSWORD=Root123; fi;

python manage.py create_tokens --password="$ROOT_PASSWORD" --token="$OCL_API_TOKEN" --create

echo "Settings for: $SETTINGS"
echo "Configurations for: $CONFIG"

python manage.py syncdb --noinput --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

echo "Importing Lookup Values"
python manage.py import_lookup_values

echo "Starting the server"
python manage.py runserver 0.0.0.0:8000 --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"