"""
Load the CNTT (khoá 27-28) curriculum into the `courses` table.

Source: chương trình đào tạo Công nghệ thông tin (the two screenshots provided).
Target program: academic_program id=1 ("Chương trình đào tạo CNTT khoá 27 - 28").

Rule for the "Ho" (chuyên ngành) column:
  - empty  -> môn chung: replicated to ALL 6 chuyên ngành (majors)
  - a value (e.g. ATTT, KHDL, "HTTT/KTPM") -> only that/those chuyên ngành

Because `Course.major` is a single FK, a common course becomes one row per major.

The script is idempotent: it deletes every course row attached to the program's
majors (which also removes the previous 7 test rows) and reloads from scratch,
inside a single transaction.

Credentials are read from the project .env (python-decouple style file).
"""
from pathlib import Path
import psycopg

# --- read DB credentials from .env -------------------------------------------
def load_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = load_env(Path(__file__).resolve().parent.parent / ".env")

# --- chuyên ngành (major) code -> id, for academic_program id=1 ---------------
# (resolved from DB; see majors table)
MAJOR = {
    "ROBOTAI": 1,
    "KHDL": 2,
    "HTTT": 3,
    "KTPM": 5,
    "ATTT": 6,
    "TKDH": 7,
}
ALL_MAJORS = [MAJOR[c] for c in ("ROBOTAI", "KHDL", "HTTT", "KTPM", "ATTT", "TKDH")]

# --- curriculum: (code, name, credits, group, ho) ----------------------------
# ho = None  -> common (all majors);  ho = ["ATTT", ...] -> those majors
GROUPS = {
    "I.1":   "Giáo dục đại cương - Bắt buộc",
    "I.2":   "Kỹ năng bổ trợ bắt buộc",
    "I.3":   "Ngoại ngữ tự chọn",
    "II.1":  "Cơ sở ngành - Bắt buộc",
    "II.2":  "Cơ sở ngành - Bắt buộc tự chọn",
    "III.1": "Chuyên ngành - Bắt buộc",
    "III.2": "Chuyên ngành - Bắt buộc tự chọn (0501)",
    "III.3": "Chuyên ngành - Bắt buộc tự chọn (0701)",
}

COURSES = [
    # ---- I.1 Giáo dục đại cương - Bắt buộc (common) ----
    ("PHE0251", "Giáo dục thể chất 1 (*)", 1, "I.1", None),
    ("PHE0261", "Giáo dục thể chất 2 (*)", 1, "I.1", None),
    ("PHE0271", "Giáo dục thể chất 3 (*)", 1, "I.1", None),
    ("POL0043", "Triết học Mác - Lênin", 3, "I.1", None),
    ("POL0052", "Kinh tế chính trị Mác - Lênin", 2, "I.1", None),
    ("POL0062", "Chủ nghĩa xã hội khoa học", 2, "I.1", None),
    ("POL0032", "Tư tưởng Hồ Chí Minh", 2, "I.1", None),
    ("POL0072", "Lịch sử Đảng Cộng sản Việt Nam", 2, "I.1", None),
    ("MIL0013", "Giáo dục quốc phòng - an ninh 1 (*)", 3, "I.1", None),
    ("MIL0022", "Giáo dục quốc phòng - an ninh 2 (*)", 2, "I.1", None),
    ("MIL0032", "Giáo dục quốc phòng - an ninh 3 (*)", 2, "I.1", None),
    ("MIL0072", "Giáo dục quốc phòng - an ninh 4 (*)", 2, "I.1", None),
    ("ENG1614", "Tiếng Anh 1", 4, "I.1", None),
    ("ENG1624", "Tiếng Anh 2", 4, "I.1", None),
    ("ENG1634", "Tiếng Anh 3", 4, "I.1", None),
    ("ENG1644", "Tiếng Anh 4", 4, "I.1", None),
    ("ENG1654", "Tiếng Anh 5", 4, "I.1", None),
    ("ENG1664", "Tiếng Anh nâng cao", 4, "I.1", None),
    ("MAT0193", "Toán cao cấp", 3, "I.1", None),
    ("MAT0013", "Lý thuyết xác suất và thống kê toán", 3, "I.1", None),
    ("LAW0492", "Pháp luật đại cương", 2, "I.1", None),
    # ---- I.2 Kỹ năng bổ trợ bắt buộc (common) ----
    ("SKI0061", "Kỹ năng tư duy phản biện", 1, "I.2", None),
    ("SKI0091", "Kỹ năng khởi nghiệp", 1, "I.2", None),
    ("SKI0011", "Kỹ năng thuyết trình", 1, "I.2", None),
    ("SKI0021", "Kỹ năng lễ tân, khánh tiết, giao tiếp", 1, "I.2", None),
    ("SKI0071", "Kỹ năng võ thuật tự vệ", 1, "I.2", None),
    # ---- I.3 Ngoại ngữ tự chọn (common) ----
    ("CHN0052", "Tiếng Hoa 1", 2, "I.3", None),
    ("CHN0062", "Tiếng Hoa 2", 2, "I.3", None),
    ("JAP0044", "Tiếng Nhật 1", 4, "I.3", None),
    ("KOR0044", "Tiếng Hàn 1", 4, "I.3", None),
    # ---- II.1 Cơ sở ngành - Bắt buộc (common) ----
    ("INF1383", "Tin học cơ sở", 3, "II.1", None),
    ("INF0433", "Nhập môn lập trình", 3, "II.1", None),
    ("INF0802", "Giới thiệu ngành và Kỹ năng nghề nghiệp", 2, "II.1", None),
    ("INF0073", "Cấu trúc dữ liệu và giải thuật", 3, "II.1", None),
    ("INF0203", "Lập trình hướng đối tượng và ứng dụng", 3, "II.1", None),
    ("INF0083", "Cơ sở dữ liệu", 3, "II.1", None),
    ("INF0263", "Mạng máy tính", 3, "II.1", None),
    ("INF1393", "Kiến trúc máy tính", 3, "II.1", None),
    ("INF0153", "Hệ điều hành", 3, "II.1", None),
    ("INF1403", "Anh văn chuyên ngành CNTT", 3, "II.1", None),
    ("INF1133", "Lập trình hệ thống", 3, "II.1", None),
    ("INF0103", "Nhập môn Trí tuệ nhân tạo", 3, "II.1", None),
    # ---- II.2 Cơ sở ngành - Bắt buộc tự chọn (common) ----
    ("INF0823", "Thiết kế web", 3, "II.2", None),
    ("BSC0092", "Phương pháp luận nghiên cứu khoa học", 2, "II.2", None),
    ("INF0992", "Công nghệ IoT", 2, "II.2", None),
    ("INF0243", "Lập trình web", 3, "II.2", None),
    ("INF1033", "Xây dựng HTTT trên các framework", 3, "II.2", None),
    ("INF0283", "Lập trình .NET và C#", 3, "II.2", None),
    ("INF0322", "Thương mại điện tử và ứng dụng", 2, "II.2", None),
    ("INF0912", "An ninh mạng", 2, "II.2", None),
    ("INF0303", "Lập trình trên thiết bị di động", 3, "II.2", None),
    ("INF1253", "Công nghệ phần mềm tiên tiến", 3, "II.2", None),
    # ---- III.1 Chuyên ngành - Bắt buộc (common) ----
    ("INF1003", "Điện toán đám mây", 3, "III.1", None),
    ("INF1313", "Quản trị dự án công nghệ thông tin", 3, "III.1", None),
    ("INF0983", "Nhập môn khoa học dữ liệu", 3, "III.1", None),
    ("INF1453", "Đồ họa máy tính", 3, "III.1", None),
    ("INF1293", "Phân tích dữ liệu lớn", 3, "III.1", None),
    ("INF1522", "Dự án nghề cơ bản", 2, "III.1", None),
    ("INF1532", "Dự án nghề nâng cao", 2, "III.1", None),
    ("INF1543", "Thực tập tốt nghiệp", 3, "III.1", None),
    ("INF0137", "Đồ án tốt nghiệp (**)", 7, "III.1", None),
    # ---- III.2 Chuyên ngành - Bắt buộc tự chọn 0501 (specific) ----
    ("INF0653", "Kiến trúc phần mềm hiện đại", 3, "III.2", ["HTTT", "KTPM"]),
    ("INF0893", "Mật mã và An toàn thông tin", 3, "III.2", ["ATTT"]),
    ("INF1413", "Cơ sở tạo hình", 3, "III.2", ["TKDH"]),
    ("INF1063", "Học máy", 3, "III.2", ["ROBOTAI", "KHDL"]),
    ("INF1073", "Xử lý ngôn ngữ tự nhiên", 3, "III.2", ["ROBOTAI", "KHDL"]),
    ("INF1423", "Thiết kế hình ảnh", 3, "III.2", ["TKDH"]),
    ("INF1433", "Thiết kế minh hoạ", 3, "III.2", ["TKDH"]),
    ("INF0903", "Thâm nhập và phòng thủ", 3, "III.2", ["ATTT"]),
    ("INF1283", "Phân tích và đánh giá An toàn thông tin", 3, "III.2", ["ATTT"]),
    ("INF0863", "Lập trình Games", 3, "III.2", ["KTPM"]),
    ("INF1443", "Thiết kế UX/UI", 3, "III.2", ["KTPM"]),
    ("INF1053", "Quản trị hệ thống thông tin", 3, "III.2", ["HTTT"]),
    ("INF1363", "Kỹ thuật phân tích yêu cầu", 3, "III.2", ["HTTT"]),
    ("INF1143", "Xử lý ảnh số và thị giác máy tính", 3, "III.2", ["ROBOTAI", "KHDL"]),
    ("INF1203", "Hệ thống thông minh", 3, "III.2", ["HTTT"]),
    # ---- III.3 Chuyên ngành - Bắt buộc tự chọn 0701 (specific) ----
    ("INF0953", "An ninh cơ sở dữ liệu", 3, "III.3", ["ATTT"]),
    ("INF1243", "Phân tích mã độc và kỹ thuật dịch ngược", 3, "III.3", ["ATTT"]),
    ("INF1213", "Robot công nghiệp", 3, "III.3", ["ROBOTAI"]),
    ("INF1463", "Khai phá dữ liệu", 3, "III.3", ["KHDL"]),
    ("INF1473", "Học sâu", 3, "III.3", ["KHDL", "ROBOTAI"]),
    ("INF1483", "Thiết kế đa truyền thông", 3, "III.3", ["TKDH"]),
    ("INF1493", "Thiết kế đồ họa", 3, "III.3", ["TKDH"]),
    ("INF1353", "Phát triển ứng dụng Thực tế ảo", 3, "III.3", ["KTPM"]),
    ("INF1303", "Phân tích dữ liệu kinh doanh", 3, "III.3", ["KTPM", "HTTT"]),
    ("INF0853", "Cơ sở dữ liệu phân tán", 3, "III.3", ["HTTT"]),
    ("INF1023", "Khoa học dữ liệu và ứng dụng", 3, "III.3", ["KHDL"]),
    ("INF1083", "Phát triển ứng dụng trí tuệ nhân tạo", 3, "III.3", ["ROBOTAI"]),
    ("INF1503", "Xử lý hậu kỳ", 3, "III.3", ["TKDH"]),
    ("INF1263", "Kiểm thử phần mềm", 3, "III.3", ["KTPM"]),
    ("INF1513", "Phân tích thiết kế hệ thống thông tin", 3, "III.3", ["HTTT"]),
    ("INF1273", "Bảo mật IoT", 3, "III.3", ["ATTT"]),
]


def build_rows():
    rows = []
    for code, name, tc, group, ho in COURSES:
        majors = ALL_MAJORS if ho is None else [MAJOR[c] for c in ho]
        desc = GROUPS[group]
        for mid in majors:
            rows.append((mid, code, name, tc, desc))
    return rows


def main():
    rows = build_rows()
    # sanity: 61 common * 6 + specific
    print(f"Curriculum courses: {len(COURSES)}  ->  rows to insert: {len(rows)}")

    conn = psycopg.connect(
        host=ENV["DATABASE_HOST"], port=int(ENV.get("DATABASE_PORT", 5432)),
        dbname=ENV["DATABASE_NAME"], user=ENV["DATABASE_USER"],
        password=ENV["DATABASE_PASSWORD"],
        options=f"-c search_path={ENV.get('DATABASE_SCHEMA', 'public')}",
    )
    with conn:
        with conn.cursor() as cur:
            # Identify the rows currently in `courses` (the 7 test rows).
            cur.execute("SELECT id FROM courses;")
            old_ids = [r[0] for r in cur.fetchall()]
            # Safety guard: refuse to run if the table already looks like the
            # loaded curriculum (prevents a re-run from nuking real data + its
            # app-created classes/CLOs).
            if len(old_ids) > 20:
                raise SystemExit(
                    f"Aborting: courses table already has {len(old_ids)} rows "
                    "(curriculum likely already loaded). Delete manually if intended."
                )
            if old_ids:
                # Remove dependent test rows in FK order: exams -> clo_types/classes.
                cur.execute(
                    "SELECT id FROM clo_types WHERE course_id = ANY(%s);", (old_ids,)
                )
                clo_ids = [r[0] for r in cur.fetchall()]
                cur.execute(
                    "SELECT id FROM classes WHERE course_id = ANY(%s);", (old_ids,)
                )
                class_ids = [r[0] for r in cur.fetchall()]
                if clo_ids or class_ids:
                    cur.execute(
                        "DELETE FROM exams WHERE clo_type_id = ANY(%s) "
                        "OR course_class_id = ANY(%s);",
                        (clo_ids or [0], class_ids or [0]),
                    )
                    print(f"Deleted dependent exams: {cur.rowcount}")
                cur.execute("DELETE FROM clo_types WHERE course_id = ANY(%s);", (old_ids,))
                print(f"Deleted dependent clo_types: {cur.rowcount}")
                cur.execute("DELETE FROM classes WHERE course_id = ANY(%s);", (old_ids,))
                print(f"Deleted dependent classes: {cur.rowcount}")
            cur.execute("DELETE FROM courses WHERE id = ANY(%s);", (old_ids or [0],))
            print(f"Deleted old course rows: {cur.rowcount}")
            cur.executemany(
                """INSERT INTO courses
                   (major_id, code, name, number_of_credits, description,
                    created_at, updated_at, deleted_at)
                   VALUES (%s, %s, %s, %s, %s, now(), now(), NULL)""",
                rows,
            )
            print(f"Inserted course rows: {len(rows)}")
    # report
    with conn.cursor() as cur:
        cur.execute(
            """select m.code, m.name, count(c.id)
               from majors m left join courses c
                 on c.major_id = m.id and c.deleted_at is null
               where m.academic_program_id = 1 and m.deleted_at is null
               group by m.code, m.name order by m.code;"""
        )
        print("\nCourses per chuyên ngành:")
        for code, name, n in cur.fetchall():
            print(f"  {code:12} {name:38} {n}")
        cur.execute("select count(*) from courses where deleted_at is null;")
        print("Total active courses:", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
