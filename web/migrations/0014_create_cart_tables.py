from django.conf import settings
from django.db import migrations
from django.db.utils import OperationalError, ProgrammingError


def create_cart_tables(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Get current database name and engine
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"Running migration in database: {db_name}")

            # Create tables if they don't exist
            print("Creating Cart table if not exists...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS web_cart (
                    id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    session_key varchar(40) NOT NULL DEFAULT '',
                    created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    user_id int NULL,
                    CONSTRAINT fk_cart_user
                        FOREIGN KEY (user_id)
                        REFERENCES auth_user(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            )
            print("Cart table creation completed")

            print("Creating CartItem table if not exists...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS web_cartitem (
                    id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    cart_id int NOT NULL,
                    course_id int NULL,
                    session_id int NULL,
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
            print("CartItem table creation completed")
            print("Migration completed successfully")
    except (OperationalError, ProgrammingError) as e:
        print(f"Error in create_cart_tables: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        raise


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("web", "0013_add_session_price"),
    ]

    operations = [
        migrations.RunPython(create_cart_tables, migrations.RunPython.noop),
    ]
