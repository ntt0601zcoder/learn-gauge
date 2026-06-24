"""
Generate demo data for the teacher CLO report: classes -> MCQ exams -> per-student
results. The "báo cáo CLO của giảng viên" is GET /apis/exams/?class=<id>, which
aggregates exam_results into pass-rate + A–F classification per CLO.

4 MCQ classes, each assigned to a different existing teacher, different course:
  1. INF1033 (42 real students from the provided roster)
  2..4. other courses with realistic fake students
(INF0083 CSDL, INF0103 Nhập môn AI, INF0823 Thiết kế web were dropped — not MCQ;
 INF1403 Anh văn chuyên ngành CNTT added in their place.)

Each class: 1 MCQ exam tied to the course's evaluation CLO (or its only CLO),
HK2 / năm 2025, max_score 6 (điểm CLO tối đa 6 = 60% học phần; Điểm thang 10 =
thực tế / 6 × 10), clo_pass_threshold 5.0. Per-student results are
drawn per-question (Bernoulli by difficulty) so grades spread realistically.
MCQ score = (correct_easy + correct_medium) / (easy + medium) * 10  (hard not graded).

Idempotent: deletes the demo classes (and their exams/results, in FK order) and
rebuilds. Deterministic (fixed RNG seed). Credentials from .env.
"""
import json
import random
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent.parent
random.seed(20260624)

# ---- the real INF1033 roster (Mã SV, Họ lót + Tên) ----
INF1033_STUDENTS = [
    ("24050023", "Mai Kim Bảo"), ("24050028", "Dương Công Danh"),
    ("24050020", "Hồ Quốc Duy"), ("24050065", "Nguyễn Khánh Duy"),
    ("24050045", "Trương Trọng Duy"), ("24050024", "Trịnh Văn Giang"),
    ("24050012", "Nguyễn Trung Hậu"), ("24050039", "Nguyễn Hoàng Trung Hiếu"),
    ("24050034", "Nguyễn Quang Hiếu"), ("24050008", "Lữ Huyền Hoà"),
    ("24050132", "Vũ Duy Hùng"), ("21050067", "Trần Văn Nhật Huy"),
    ("24050004", "Huỳnh Tấn Hưng"), ("24050013", "Nguyễn Thanh Kha"),
    ("24050036", "Nguyễn Trương Anh Khoa"), ("24050027", "Lê Huỳnh Quốc Kiệt"),
    ("24050010", "Nguyễn Thị Thanh Lam"), ("24050002", "Phan Nguyễn Thành Long"),
    ("24050030", "Phạm Đức Lộc"), ("21050040", "Nguyễn Minh Mẫn"),
    ("24050042", "Chung Võ Quốc Minh"), ("24050006", "Phạm Nhật Minh"),
    ("24050007", "Nguyễn Thị Ngọc Nga"), ("24050001", "Nguyễn Chấn Nguyên"),
    ("22050030", "Vy Ngọc Nhân"), ("24050025", "Nguyễn Quang Nhật"),
    ("24050011", "Nguyễn Mai Yến Nhi"), ("24050033", "Voòng Sìn Phát"),
    ("24050031", "Trần Thanh Phong"), ("24050019", "Nguyễn Hoàng Phúc"),
    ("24050133", "Nguyễn Trọng Phước"), ("24050029", "Trần Tấn Tài"),
    ("24050018", "Lý Thanh Tâm"), ("24050009", "Lương Xuân Thái"),
    ("24050035", "Lê Chí Thành"), ("24050021", "Huỳnh Minh Thắng"),
    ("24050043", "Lê Anh Thắng"), ("24050026", "Lê Văn Thắng"),
    ("22050008", "Bùi Văn Anh Thế"), ("24050003", "Nguyễn Hoàng Thiện"),
    ("24050032", "Lê Trọng Tiến"), ("24050040", "Nguyễn Thế Vinh"),
]

# course_code, major_code, teacher_card_id, group, real_students(optional)
CLASS_SPECS = [
    ("INF1033", "HTTT24-26", "90867", "01", INF1033_STUDENTS),
    ("INF0433", "ROBOTAI24-26", "91073", "02", None),
    ("INF0263", "ATTT24-26", "90514", "01", None),
    ("INF1403", "KTPM24-26", "90822", "01", None),  # Anh văn chuyên ngành CNTT (thay CSDL)
]

FAMILY = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
          "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trương", "Cao"]
MIDDLE = ["Văn", "Hữu", "Đức", "Minh", "Quang", "Thanh", "Hoàng", "Ngọc", "Gia",
          "Tuấn", "Anh", "Công", "Xuân", "Bá", "Thị", "Như", "Khánh", "Trọng"]
GIVEN = ["An", "Bình", "Cường", "Dũng", "Giang", "Hà", "Hải", "Hoà", "Hùng",
         "Khoa", "Long", "Minh", "Nam", "Phong", "Phúc", "Quân", "Sơn", "Tâm",
         "Thành", "Thắng", "Tiến", "Trung", "Tú", "Vinh", "Linh", "Hương", "Lan",
         "Mai", "Ngân", "Nhi", "Trang", "Vy", "Khang", "Đạt", "Nghĩa", "Lộc"]


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


def fake_students(n, base):
    out = []
    for i in range(n):
        name = f"{random.choice(FAMILY)} {random.choice(MIDDLE)} {random.choice(GIVEN)}"
        out.append((f"2405{base + i:04d}", name))
    return out


def gen_result(student):
    """Per-question Bernoulli by difficulty -> realistic grade spread."""
    e, m, h = 20, 15, 5
    acc = min(1.0, max(0.15, random.gauss(0.70, 0.16)))
    ce = sum(1 for _ in range(e) if random.random() < min(1.0, acc + 0.10))
    cm = sum(1 for _ in range(m) if random.random() < acc)
    ch = sum(1 for _ in range(h) if random.random() < max(0.0, acc - 0.15))
    return (student[0], student[1], e + m + h, e, m, h, ce, cm, ch)


def grade(ce, cm, e=20, m=15):
    s = (ce + cm) / (e + m) * 10
    return "A" if s >= 8.5 else "B" if s >= 7.0 else "C" if s >= 5.5 else "D" if s >= 4.0 else "F"


def main():
    conn = psycopg.connect(
        host=ENV["DATABASE_HOST"], port=int(ENV.get("DATABASE_PORT", 5432)),
        dbname=ENV["DATABASE_NAME"], user=ENV["DATABASE_USER"],
        password=ENV["DATABASE_PASSWORD"],
        options=f"-c search_path={ENV.get('DATABASE_SCHEMA', 'public')}",
    )
    summary = []
    with conn:
        with conn.cursor() as cur:
            # idempotent reset in FK order (DB FKs don't cascade). Wipe ALL classes
            # — the only classes in this system are demo data — so dropped courses
            # (e.g. CSDL/AI/Web Design) don't linger.
            cur.execute("SELECT id FROM classes;")
            cids = [r[0] for r in cur.fetchall()]
            if cids:
                cur.execute("SELECT id FROM exams WHERE course_class_id = ANY(%s);", (cids,))
                eids = [r[0] for r in cur.fetchall()]
                if eids:
                    cur.execute("DELETE FROM exam_results WHERE exam_id = ANY(%s);", (eids,))
                    cur.execute("DELETE FROM essay_exam_results WHERE exam_id = ANY(%s);", (eids,))
                    cur.execute("DELETE FROM exams WHERE id = ANY(%s);", (eids,))
                cur.execute("DELETE FROM classes WHERE id = ANY(%s);", (cids,))
                print(f"Reset: removed {len(cids)} old demo classes")

            base = 6000
            for code, major, tcard, group, real in CLASS_SPECS:
                # resolve course replica, teacher, clo_type
                cur.execute(
                    """SELECT c.id, c.name FROM courses c JOIN majors m ON m.id=c.major_id
                       WHERE c.code=%s AND m.code=%s AND c.deleted_at IS NULL;""",
                    (code, major),
                )
                course_id, course_name = cur.fetchone()
                cur.execute("SELECT id FROM users WHERE card_id=%s AND role='teacher';", (tcard,))
                teacher_id = cur.fetchone()[0]
                # prefer the evaluation CLO; else highest weight
                cur.execute(
                    """SELECT id, name FROM clo_types WHERE course_id=%s AND deleted_at IS NULL
                       ORDER BY is_evaluation DESC, weight DESC LIMIT 1;""",
                    (course_id,),
                )
                clo_id, clo_name = cur.fetchone()

                class_code = f"{code}.{group}"
                cur.execute(
                    """INSERT INTO classes
                       (course_id, teacher_id, code, name, semester, year, description,
                        created_at, updated_at, deleted_at)
                       VALUES (%s,%s,%s,%s,2,2025,%s, now(), now(), NULL) RETURNING id;""",
                    (course_id, teacher_id, class_code,
                     f"{course_name} - Nhóm {group}",
                     "Lớp học phần HK2 năm học 2025-2026"),
                )
                class_id = cur.fetchone()[0]

                cur.execute(
                    """INSERT INTO exams
                       (course_class_id, name, description, clo_type_id, exam_format,
                        chapters, pass_expectation_rate, clo_pass_threshold, max_score,
                        created_at, updated_at, deleted_at)
                       VALUES (%s,%s,%s,%s,'MCQ',%s,80,5.0,6, now(), now(), NULL) RETURNING id;""",
                    (class_id, f"{course_name} - Thi cuối kỳ",
                     "Bài thi trắc nghiệm cuối kỳ", clo_id, Jsonb([1, 2, 3, 4, 5])),
                )
                exam_id = cur.fetchone()[0]

                students = real if real else fake_students(random.randint(36, 42), base)
                if not real:
                    base += 200
                results = [gen_result(s) for s in students]
                cur.executemany(
                    """INSERT INTO exam_results
                       (student_code, student_name, exam_id, total_questions,
                        total_easy_questions, total_medium_questions, total_hard_questions,
                        total_correct_easy_questions, total_correct_medium_questions,
                        total_correct_hard_questions, created_at, updated_at)
                       VALUES (%s,%s,""" + str(exam_id) + """,%s,%s,%s,%s,%s,%s,%s, now(), now());""",
                    results,
                )
                # summary
                # result tuple: 6=correct_easy, 7=correct_medium, 8=correct_hard
                grades = [grade(r[6], r[7]) for r in results]
                dist = {g: grades.count(g) for g in "ABCDF"}
                npass = sum(1 for r in results if (r[6] + r[7]) / 35 * 10 >= 5.0)
                summary.append((class_code, course_name, tcard, clo_name, len(results),
                                round(npass / len(results) * 100), dist))

    print(f"\n{'Class':14}{'Teacher':8}{'CLO':18}{'N':>4}{'Pass%':>7}  A/B/C/D/F")
    for cc, cn, tc, clo, n, pr, d in summary:
        print(f"  {cc:13}{tc:8}{clo:18}{n:>4}{pr:>6}%  "
              f"{d['A']}/{d['B']}/{d['C']}/{d['D']}/{d['F']}  ({cn[:24]})")

    # verify no zero-result exams (would 500 the report)
    with conn.cursor() as cur:
        cur.execute("""SELECT count(*) FROM exams e WHERE e.deleted_at IS NULL
                       AND NOT EXISTS (SELECT 1 FROM exam_results r WHERE r.exam_id=e.id);""")
        print("\nExams with zero results (must be 0):", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM classes;")
        nc = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM exams;")
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM exam_results;")
        nr = cur.fetchone()[0]
        print(f"Totals -> classes={nc} exams={ne} exam_results={nr}")
    conn.close()


if __name__ == "__main__":
    main()
