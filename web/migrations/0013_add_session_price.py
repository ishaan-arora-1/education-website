from django.db import migrations
from django.db.utils import OperationalError


def add_price_column(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Check if column exists
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM pragma_table_info('web_session')
                WHERE name='price'
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
