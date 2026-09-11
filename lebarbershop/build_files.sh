#!/bin/bash
# build_files.sh

echo "Installation des dépendances..."
pip install -r requirements.txt

echo "Application des migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --fake-initial

echo "Collection des fichiers statiques..."
python manage.py collectstatic --noinput