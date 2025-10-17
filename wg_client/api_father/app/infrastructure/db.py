import os
import pymysql


def get_dsn_and_db():
    mode = os.getenv("DB_MODE", "test").lower()
    if mode == "prod":
        host = os.getenv("DB_PROD_HOST")
        port = int(os.getenv("DB_PROD_PORT", "3306"))
        user = os.getenv("DB_PROD_USER")
        password = os.getenv("DB_PROD_PASSWORD")
        name = os.getenv("DB_PROD_NAME", "tzserver")
    else:
        host = os.getenv("DB_TEST_HOST", "db")
        port = int(os.getenv("DB_TEST_PORT", "3306"))
        user = os.getenv("DB_TEST_USER", "tzuser")
        password = os.getenv("DB_TEST_PASSWORD", "tzpass")
        name = os.getenv("DB_TEST_NAME", "tzserver")
    dsn = dict(
        host=host, 
        port=port, 
        user=user, 
        password=password, 
        database=name, 
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
        use_unicode=True
    )
    return dsn, name



