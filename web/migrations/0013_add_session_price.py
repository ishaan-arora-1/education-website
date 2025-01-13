from django.db import migrations
from django.db.utils import OperationalError


def add_price_column(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Get current database name
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]

            # Check if column exists
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = '{db_name}'
                AND table_name = 'web_session'
                AND column_name = 'price'
            """
            )
            if cursor.fetchone()[0] == 0:
                # Only add the column if it doesn't exist
                cursor.execute(
                    """
                    ALTER TABLE web_session
                    ADD COLUMN price decimal(10,2) NULL
                """
                )
    except OperationalError:
        # Column already exists, skip
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0012_fix_cart_session_key"),
    ]

    operations = [
        migrations.RunPython(add_price_column, migrations.RunPython.noop),
    ]
