# Card Control

#### First Time

```bash
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
```

```python
# python manage.py shell
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())  # Create a `.env` file in the root folder and add this value with key `DJANGO_SECRET_KEY`
```

#### On Updates

```bash
python manage.py makemigrations core
python manage.py migrate
```
