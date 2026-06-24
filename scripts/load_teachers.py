"""
(Re)create the teacher (giảng viên) accounts from the provided list.

- card_id  = Mã nhân viên (e.g. 90867, LT001)
- fullname = Họ tên
- email    = given.family@learngauge.edu.vn (no diacritics) — matches the
             existing teacher convention (e.g. an.nguyen@...)
- password = shared default "Teacher@2024", hashed with Django-compatible
             pbkdf2_sha256 (random per-user salt) so users can log in / be
             re-hashed by Django normally.
- status   = activated, role = teacher, gender = other, birth_date = null, phone = ''

Replaces the existing sample teachers: deletes all role='teacher' rows (safe —
0 classes reference them) and inserts these 10. Idempotent.
"""
import base64
import hashlib
import secrets
import unicodedata
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parent.parent
EMAIL_DOMAIN = "bdu.edu.vn"
DEFAULT_PASSWORD = "Teacher@2024"
PBKDF2_ITERATIONS = 870000  # Django 5.1 default; verification reads this from the hash

# (card_id, fullname) — order as provided
TEACHERS = [
    ("90867", "Lê Duy Hùng"),
    ("90822", "Dương Anh Tuấn"),
    ("91073", "Dương Quang Sinh"),
    ("90514", "Huỳnh Quang Đức"),
    ("90701", "Nguyễn Văn Thành"),
    ("90919", "Bùi Đức Thành"),
    ("91061", "Đỗ Trí Nhứt"),
    ("90794", "Nguyễn Thanh Kỳ"),
    ("90928", "Nguyễn Hồ Hải"),
    ("LT001", "Nguyễn Thanh Sơn"),
]


def load_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env(ROOT / ".env")


def no_accent(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def make_email(fullname):
    toks = no_accent(fullname).split()
    given = toks[-1].lower()
    family = toks[0].lower()
    return f"{given}.{family}@{EMAIL_DOMAIN}"


def django_pbkdf2(password, iterations=PBKDF2_ITERATIONS):
    """Produce a Django-compatible pbkdf2_sha256 password hash string."""
    salt = "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        for _ in range(22)
    )
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    h = base64.b64encode(dk).decode().strip()
    return f"pbkdf2_sha256${iterations}${salt}${h}"


def main():
    rows = []
    seen = set()
    print("Planned teacher accounts:")
    for card_id, fullname in TEACHERS:
        email = make_email(fullname)
        assert email not in seen, f"duplicate email {email}"
        seen.add(email)
        rows.append((django_pbkdf2(DEFAULT_PASSWORD), card_id, fullname, email))
        print(f"  {card_id:8} {fullname:20} -> {email}")

    conn = psycopg.connect(
        host=ENV["DATABASE_HOST"], port=int(ENV.get("DATABASE_PORT", 5432)),
        dbname=ENV["DATABASE_NAME"], user=ENV["DATABASE_USER"],
        password=ENV["DATABASE_PASSWORD"],
        options=f"-c search_path={ENV.get('DATABASE_SCHEMA', 'public')}",
    )
    with conn:
        with conn.cursor() as cur:
            # guard: never touch root/student
            cur.execute("SELECT id, card_id, email FROM users WHERE role='teacher';")
            old = cur.fetchall()
            print(f"\nDeleting existing teacher accounts: {len(old)} -> {[o[1] for o in old]}")
            cur.execute("DELETE FROM users WHERE role='teacher';")

            cur.executemany(
                """INSERT INTO users
                   (password, card_id, fullname, birth_date, gender, email, phone,
                    status, role, last_login, created_at, updated_at)
                   VALUES (%s, %s, %s, NULL, 'other', %s, '',
                           'activated', 'teacher', NULL, now(), now())""",
                rows,
            )
            print(f"Inserted teacher accounts: {len(rows)}")

    # verify
    with conn.cursor() as cur:
        cur.execute(
            "SELECT card_id, fullname, email, status, role, "
            "split_part(password,'$',1) FROM users WHERE role='teacher' "
            "ORDER BY card_id;"
        )
        print("\nTeachers now in DB:")
        for r in cur.fetchall():
            print("  ", r)
        cur.execute("SELECT role, count(*) FROM users GROUP BY role ORDER BY role;")
        print("\nUser counts by role:", cur.fetchall())
    conn.close()
    print(f"\nDefault password for all 10: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
