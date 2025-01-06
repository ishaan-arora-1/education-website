cd /home/alphaonelabs99282llkb/web/
git reset --hard HEAD
git pull

if find /home/alphaonelabs99282llkb/web/requirements.txt -mmin -60 | grep -q .; then
    pip install -r requirements.txt
fi
# only run these if the migration folder changed
python manage.py migrate
# only run this if there are new static files
python manage.py collectstatic --noinput