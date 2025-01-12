from django.conf import settings
from django.db import migrations
from django.db.utils import OperationalError, ProgrammingError


def create_cart_tables(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Get current database name
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]

            # Check if Cart table exists
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = '{db_name}'
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                )

                # Create trigger for cart validation
                cursor.execute(
                    """
                    CREATE TRIGGER cart_user_or_session_key_trigger
                    BEFORE INSERT ON web_cart
                    FOR EACH ROW
                    BEGIN
                        IF NEW.user_id IS NULL AND NEW.session_key = '' THEN
                            SIGNAL SQLSTATE '45000'
                            SET MESSAGE_TEXT = 'Either user_id must not be NULL or session_key must not be empty';
                        END IF;
                    END;
                """
                )

                cursor.execute(
                    """
                    CREATE TRIGGER cart_user_or_session_key_update_trigger
                    BEFORE UPDATE ON web_cart
                    FOR EACH ROW
                    BEGIN
                        IF NEW.user_id IS NULL AND NEW.session_key = '' THEN
                            SIGNAL SQLSTATE '45000'
                            SET MESSAGE_TEXT = 'Either user_id must not be NULL or session_key must not be empty';
                        END IF;
                    END;
                """
                )

            # Check if CartItem table exists
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = '{db_name}'
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                )
    except (OperationalError, ProgrammingError) as e:
        # Log the error for debugging
        print(f"Error in create_cart_tables: {str(e)}")
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
