from django.conf import settings
from django.db import migrations
from django.db.utils import OperationalError, ProgrammingError


def create_cart_tables(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Check if Cart table exists
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = 'web_cart'
            """
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    CREATE TABLE web_cart (
                        id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        session_key varchar(40) NOT NULL DEFAULT '',
                        created_at datetime(6) NOT NULL,
                        updated_at datetime(6) NOT NULL,
                        user_id bigint NULL,
                        CONSTRAINT fk_cart_user
                            FOREIGN KEY (user_id)
                            REFERENCES auth_user(id)
                            ON DELETE CASCADE
                    )
                """
                )

            # Check if CartItem table exists
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = 'web_cartitem'
            """
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    CREATE TABLE web_cartitem (
                        id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        created_at datetime(6) NOT NULL,
                        updated_at datetime(6) NOT NULL,
                        cart_id bigint NOT NULL,
                        course_id bigint NULL,
                        session_id bigint NULL,
                        CONSTRAINT fk_cartitem_cart
                            FOREIGN KEY (cart_id)
                            REFERENCES web_cart(id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_cartitem_course
                            FOREIGN KEY (course_id)
                            REFERENCES web_course(id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_cartitem_session
                            FOREIGN KEY (session_id)
                            REFERENCES web_session(id)
                            ON DELETE CASCADE,
                        UNIQUE KEY unique_cart_course (cart_id, course_id),
                        UNIQUE KEY unique_cart_session (cart_id, session_id)
                    )
                """
                )

            # Add constraint if it doesn't exist
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_schema = DATABASE()
                AND table_name = 'web_cart'
                AND constraint_name = 'cart_user_or_session_key'
            """
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    ALTER TABLE web_cart
                    ADD CONSTRAINT cart_user_or_session_key
                    CHECK ((user_id IS NOT NULL) OR (session_key != ''))
                """
                )
    except (OperationalError, ProgrammingError):
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
