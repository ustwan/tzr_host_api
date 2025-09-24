from fastapi import FastAPI, HTTPException
import os
import pymysql

app = FastAPI(title="API_FATHER")


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
    dsn = dict(host=host, port=port, user=user, password=password, database=name, cursorclass=pymysql.cursors.DictCursor)
    return dsn, name


@app.get("/internal/health")
def health():
    return {"status": "ok"}


@app.get("/internal/constants")
def constants():
    dsn, db_name = get_dsn_and_db()
    sql = f"SELECT Name, Value, Description FROM `{db_name}`.constants ORDER BY Value ASC"
    try:
        conn = pymysql.connect(**dsn)
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    data = {row["Name"]: {"value": float(row["Value"]), "description": row["Description"]} for row in rows}
    return data
