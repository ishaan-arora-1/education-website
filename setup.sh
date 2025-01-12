cd /home/alphaonelabs99282llkb/web/
git reset --hard HEAD
git pull

if find /home/alphaonelabs99282llkb/web/requirements.txt -mmin -1 | grep -q .; then
    pip install -r requirements.txt
fi
python manage.py migrate
python manage.py collectstatic --noinput
