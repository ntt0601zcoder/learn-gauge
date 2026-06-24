"""
Load CLO (chuẩn đầu ra) data into the `clo_types` table.

Source: the "CLO / Trọng số / Trạng thái đánh giá" columns of the CNTT khoá 27
curriculum (screenshots provided by the user). Each spreadsheet assessment line
becomes ONE clo_types row:
  - name          = the CLO label(s) of that line, e.g. "CLO2" or "CLO2, CLO3"
  - weight        = the line's "Trọng số" (per-course lines sum to 100)
  - is_evaluation = the "Trạng thái đánh giá" x/X  (at most ONE per course — the
                    app enforces a single evaluation CLO per course)
  - description   = generated (Vietnamese); written by the clo-load-plan workflow
                    with a deterministic template fallback.

Because common courses were replicated across all 6 chuyên ngành, a course CODE
maps to several course rows; the CLO lines are attached to every matching row.

Idempotent: deletes existing clo_types for the affected courses, then reloads,
inside one transaction. Credentials come from the project .env.
"""
import json
import re
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = Path("/tmp/clo_map.json")            # canonical transcription
DESC_FILE = Path("/tmp/clo_descriptions.json")  # [{code, clo, description}] from workflow


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

CLO_MEANING = {
    "CLO1": "Kiến thức",
    "CLO2": "Kỹ năng",
    "CLO3": "Thái độ / Mức tự chủ và trách nhiệm",
    "CLO4": "Chuẩn đầu ra bổ sung",
    "CLO5": "Chuẩn đầu ra bổ sung",
    "CLO6": "Chuẩn đầu ra bổ sung",
}


def norm(s):
    """Normalize a CLO label for matching: drop spaces, uppercase."""
    return re.sub(r"\s+", "", s).upper()


def template_desc(course_name, clo, weight, is_eval):
    parts = [c.strip() for c in clo.split(",")]
    meanings = ", ".join(
        f"{p} ({CLO_MEANING.get(p.upper(), 'chuẩn đầu ra')})" for p in parts
    )
    role = "thành phần đánh giá chính" if is_eval else "thành phần học phần"
    return (
        f"Chuẩn đầu ra {meanings} của môn {course_name} — "
        f"trọng số {weight}%, {role}."
    )


def main():
    courses = json.loads(MAP_FILE.read_text())
    clo_by_code = {c["code"]: c for c in courses}

    # description lookup keyed by (code, normalized clo)
    desc_lookup = {}
    if DESC_FILE.exists():
        for d in json.loads(DESC_FILE.read_text()):
            desc_lookup[(d["code"], norm(d["clo"]))] = d["description"].strip()
    print(f"Loaded {len(courses)} course CLO maps, "
          f"{len(desc_lookup)} generated descriptions")

    conn = psycopg.connect(
        host=ENV["DATABASE_HOST"], port=int(ENV.get("DATABASE_PORT", 5432)),
        dbname=ENV["DATABASE_NAME"], user=ENV["DATABASE_USER"],
        password=ENV["DATABASE_PASSWORD"],
        options=f"-c search_path={ENV.get('DATABASE_SCHEMA', 'public')}",
    )

    fallback = 0
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            # all active course rows for the program's majors
            cur.execute(
                "SELECT id, code, major_id, name FROM courses "
                "WHERE major_id = ANY(%s) AND deleted_at IS NULL;",
                ([1, 2, 3, 5, 6, 7],),
            )
            course_rows = cur.fetchall()
            course_ids = [r[0] for r in course_rows]
            print(f"Target course rows: {len(course_rows)}")

            # idempotent reset
            cur.execute(
                "DELETE FROM clo_types WHERE course_id = ANY(%s);", (course_ids,)
            )
            print(f"Deleted existing clo_types: {cur.rowcount}")

            rows = []
            for cid, code, major_id, cname in course_rows:
                entry = clo_by_code.get(code)
                if not entry:
                    print(f"  WARN: no CLO map for course code {code} (id {cid})")
                    continue
                for line in entry["lines"]:
                    clo = line["clo"]
                    desc = desc_lookup.get((code, norm(clo)))
                    if not desc:
                        desc = template_desc(cname, clo, line["weight"],
                                             line["is_evaluation"])
                        fallback += 1
                    rows.append((clo, desc, bool(line["is_evaluation"]),
                                 int(line["weight"]), cid))

            cur.executemany(
                """INSERT INTO clo_types
                   (name, description, is_evaluation, weight, course_id,
                    created_at, updated_at, deleted_at)
                   VALUES (%s, %s, %s, %s, %s, now(), now(), NULL)""",
                rows,
            )
            inserted = len(rows)
            print(f"Inserted clo_types rows: {inserted} "
                  f"(template-fallback descriptions: {fallback})")

    # ---- report ----
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM clo_types WHERE deleted_at IS NULL;")
        print("Total active clo_types:", cur.fetchone()[0])
        # invariant re-check at DB level: courses with >1 evaluation CLO
        cur.execute(
            """SELECT course_id, count(*) FROM clo_types
               WHERE is_evaluation AND deleted_at IS NULL
               GROUP BY course_id HAVING count(*) > 1;"""
        )
        bad = cur.fetchall()
        print("Courses with >1 evaluation CLO (must be empty):", bad or "none")
        # weight sums per course
        cur.execute(
            """SELECT count(*) FROM (
                 SELECT course_id, sum(weight) s FROM clo_types
                 WHERE deleted_at IS NULL GROUP BY course_id
               ) t WHERE s <> 100;"""
        )
        print("Courses whose CLO weights != 100:", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
