from django.conf import settings
from django.db import migrations
from django.db.utils import OperationalError


def create_cart_tables(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Check if Cart table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='web_cart'
            """
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    CREATE TABLE web_cart (
                        id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                        session_key varchar(40) NOT NULL DEFAULT '',
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        user_id integer REFERENCES auth_user(id) ON DELETE CASCADE
                    )
                """
                )

            # Check if CartItem table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='web_cartitem'
            """
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    CREATE TABLE web_cartitem (
                        id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        cart_id integer NOT NULL REFERENCES web_cart(id) ON DELETE CASCADE,
                        course_id integer REFERENCES web_course(id) ON DELETE CASCADE,
                        session_id integer REFERENCES web_session(id) ON DELETE CASCADE,
                        UNIQUE(cart_id, course_id),
                        UNIQUE(cart_id, session_id)
                    )
                """
                )

            # Add constraint if it doesn't exist
            cursor.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='web_cart'
            """
            )
            if "cart_user_or_session_key" not in (cursor.fetchone() or [""])[0]:
                cursor.execute(
                    """
                    ALTER TABLE web_cart
                    ADD CONSTRAINT cart_user_or_session_key
                    CHECK ((user_id IS NOT NULL) OR (session_key != ''))
                """
                )
    except OperationalError:
        # Table already exists or other error, skip
        pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("web", "0013_add_session_price"),
    ]

    operations = [
        migrations.RunPython(create_cart_tables, migrations.RunPython.noop),
    ]
