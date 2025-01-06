cd /home/alphaonelabs99282llkb/web/
git reset --hard HEAD
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput