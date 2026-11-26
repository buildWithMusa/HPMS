#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [[ -n "${HPMS_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
    python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = "mosessangura2003@gmail.com"
password = os.environ["HPMS_BOOTSTRAP_ADMIN_PASSWORD"]

if len(password) < 12:
    raise SystemExit("Admin password must be at least 12 characters.")

user, created = User.objects.get_or_create(email=email)
user.set_password(password)
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.save()

print("Production administrator account configured successfully.")
PY
else
    echo "Administrator bootstrap skipped."
fi
