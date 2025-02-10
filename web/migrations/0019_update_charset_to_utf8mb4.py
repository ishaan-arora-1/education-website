from django.db import migrations


def update_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    # Convert the tables to utf8mb4
    tables = [
        "django_admin_log",  # For admin log entries
        "web_blogpost",  # For blog posts
        "web_blogcomment",  # For blog comments
        "web_forumtopic",  # For forum topics
        "web_forumreply",  # For forum replies
    ]

    with schema_editor.connection.cursor() as cursor:
        # Set the database character set
        cursor.execute("ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

        # Update each table
        for table in tables:
            cursor.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            # Update text/varchar columns specifically
            cursor.execute(
                f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table}'
                AND (DATA_TYPE = 'varchar' OR DATA_TYPE = 'text' OR DATA_TYPE = 'longtext')
            """
            )
            columns = cursor.fetchall()
            for (column,) in columns:
                cursor.execute(
                    f"""
                    ALTER TABLE {table}
                    MODIFY {column} {cursor.description[0][1]}
                    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
                )


def reverse_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    tables = [
        "django_admin_log",
        "web_blogpost",
        "web_blogcomment",
        "web_forumtopic",
        "web_forumreply",
    ]

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER DATABASE CHARACTER SET utf8 COLLATE utf8_general_ci")
        for table in tables:
            cursor.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")


class Migration(migrations.Migration):
    atomic = False  # Disable transaction wrapping for DDL operations

    dependencies = [
        ("web", "0018_alter_blogpost_title_charset"),
    ]

    operations = [
        migrations.RunPython(update_charset_mysql, reverse_charset_mysql),
    ]
