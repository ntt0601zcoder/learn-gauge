"""
Fix CLO rows for multi-CLO courses that HAVE an evaluation component.

User rule: for a course with >=2 CLOs that has any evaluation, EVERY CLO must be
its own row and ALL must be is_evaluation=True (not just one). Weights from a
grouped cell ("CLO2, CLO3") are split evenly so each course still totals 100%.

Scope: only the 10 course codes below (the ones with >=2 CLOs AND an evaluation).
All other courses are left untouched. Each code is a common course replicated
across the 6 chuyên ngành, so every replica's clo_types is rebuilt.

Idempotent: deletes clo_types of the affected course rows, reinserts the expanded
set, inside one transaction. See [[clo-types-load]] for the original load.
"""
import json
import re
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = Path("/tmp/clo_map.json")

TARGET_CODES = [
    "POL0043", "POL0052", "POL0072", "POL0032",
    "SKI0061", "SKI0091", "SKI0021",
    "INF1383", "INF1133", "INF1253",
]

CLO_MEANING = {
    "CLO1": "Kiến thức",
    "CLO2": "Kỹ năng",
    "CLO3": "Thái độ / Mức tự chủ và trách nhiệm",
    "CLO4": "Chuẩn đầu ra bổ sung",
    "CLO5": "Chuẩn đầu ra bổ sung",
    "CLO6": "Chuẩn đầu ra bổ sung",
}


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


def even_split(weight, n):
    """Distribute `weight` over n CLOs as integers summing to `weight`;
    the first `rem` CLOs get the extra +1 (e.g. 100/3 -> [34,33,33])."""
    base, rem = divmod(weight, n)
    return [base + 1 if i < rem else base for i in range(n)]


def expand(course):
    """Original lines -> per-CLO rows: split grouped cells, even-split their
    weight, mark every resulting CLO as evaluation."""
    out = []  # (clo, weight, is_evaluation)
    for line in course["lines"]:
        clos = [c.strip() for c in line["clo"].split(",")]
        weights = even_split(int(line["weight"]), len(clos))
        for clo, w in zip(clos, weights):
            out.append((clo, w, True))
    return out


def describe(course_name, clo, weight):
    meaning = CLO_MEANING.get(clo.upper(), "chuẩn đầu ra")
    return (
        f"Chuẩn đầu ra {clo} ({meaning}) của môn {course_name} — "
        f"trọng số {weight}%, thành phần đánh giá chính."
    )


def main():
    courses = {c["code"]: c for c in json.loads(MAP_FILE.read_text())}

    # Preview the new structure
    print("New CLO structure for target courses:")
    expanded = {}
    for code in TARGET_CODES:
        rows = expand(courses[code])
        expanded[code] = rows
        total = sum(w for _, w, _ in rows)
        desc = " | ".join(f"{c}({w}%,ĐG)" for c, w, _ in rows)
        assert total == 100, f"{code} total {total} != 100"
        assert all(e for *_, e in rows), f"{code} has non-eval CLO"
        print(f"  {code:8} [{total}%] {desc}")

    conn = psycopg.connect(
        host=ENV["DATABASE_HOST"], port=int(ENV.get("DATABASE_PORT", 5432)),
        dbname=ENV["DATABASE_NAME"], user=ENV["DATABASE_USER"],
        password=ENV["DATABASE_PASSWORD"],
        options=f"-c search_path={ENV.get('DATABASE_SCHEMA', 'public')}",
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, code, name FROM courses "
                "WHERE code = ANY(%s) AND deleted_at IS NULL;",
                (TARGET_CODES,),
            )
            course_rows = cur.fetchall()
            ids = [r[0] for r in course_rows]
            print(f"\nAffected course rows (10 codes x replicas): {len(course_rows)}")

            cur.execute("DELETE FROM clo_types WHERE course_id = ANY(%s);", (ids,))
            print(f"Deleted old clo_types: {cur.rowcount}")

            rows = []
            for cid, code, cname in course_rows:
                for clo, w, _ in expanded[code]:
                    rows.append((clo, describe(cname, clo, w), True, w, cid))
            cur.executemany(
                """INSERT INTO clo_types
                   (name, description, is_evaluation, weight, course_id,
                    created_at, updated_at, deleted_at)
                   VALUES (%s, %s, %s, %s, %s, now(), now(), NULL)""",
                rows,
            )
            print(f"Inserted new clo_types: {len(rows)}")

    # ---- verify ----
    with conn.cursor() as cur:
        cur.execute(
            """SELECT c.code, count(*) , sum(ct.weight::int),
                      bool_and(ct.is_evaluation)
               FROM clo_types ct JOIN courses c ON c.id = ct.course_id
               WHERE c.code = ANY(%s) AND ct.deleted_at IS NULL
               GROUP BY c.code, ct.course_id;""",
            (TARGET_CODES,),
        )
        bad = []
        per_code = {}
        for code, n, wsum, all_eval in cur.fetchall():
            per_code.setdefault(code, []).append((n, wsum, all_eval))
            if wsum != 100 or not all_eval:
                bad.append((code, n, wsum, all_eval))
        print("\nVerification per code (rows, weight_sum, all_eval) — one replica shown:")
        for code in TARGET_CODES:
            print(f"  {code:8} {per_code[code][0]}  (x{len(per_code[code])} replicas)")
        print("\nReplicas with weight!=100 or not all-eval:", bad or "none")

        cur.execute("SELECT count(*) FROM clo_types WHERE deleted_at IS NULL;")
        print("Total active clo_types now:", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
