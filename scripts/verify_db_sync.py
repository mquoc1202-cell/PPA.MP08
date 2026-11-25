import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from src.core.database import Base, engine
import src.models

def verify_db_sync():
    print("==================================================")
    print("   HỆ THỐNG KIỂM TRA ĐỒNG BỘ CƠ SỞ DỮ LIỆU SQLITE   ")
    print("==================================================")
    
    conn = sqlite3.connect("freight_dev.db")
    cursor = conn.cursor()
    
    # 1. Integrity check
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchall()
    print(f"\n1. Kiểm tra toàn vẹn vật lý (PRAGMA integrity_check):")
    print(f"   -> Kết quả: {integrity[0][0] if integrity else 'N/A'}")
    
    # 2. Foreign keys check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    print(f"\n2. Kiểm tra ràng buộc khóa ngoại (PRAGMA foreign_key_check):")
    if not fk_violations:
        print("   -> PASS: Không có vi phạm khóa ngoại nào.")
    else:
        print(f"   -> CẢNH BÁO: Phát hiện {len(fk_violations)} vi phạm:")
        for v in fk_violations:
            print(f"      * Bảng {v[0]}, RowId {v[1]}, Target {v[2]}, FK index {v[3]}")

    # 3. Tables & Schema sync
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    db_tables = {row[0] for row in cursor.fetchall()}
    model_tables = set(Base.metadata.tables.keys())
    
    print(f"\n3. So khớp danh sách bảng (Tables):")
    print(f"   - Số bảng trong SQLAlchemy Models: {len(model_tables)}")
    print(f"   - Số bảng trong freight_dev.db:     {len(db_tables)}")
    
    missing_tables = model_tables - db_tables
    extra_tables = db_tables - model_tables
    
    if missing_tables:
        print(f"   -> LỖI: Bảng có trong Model nhưng thiếu trong DB: {missing_tables}")
    else:
        print("   -> PASS: 100% các bảng trong Models đều tồn tại trong DB.")
        
    if extra_tables:
        print(f"   -> Chú ý: Bảng phụ ngoài Models: {extra_tables}")

    print(f"\n4. So khớp chi tiết từng cột và thuộc tính (Columns Sync):")
    all_columns_synced = True
    for table_name in sorted(list(model_tables)):
        if table_name not in db_tables:
            continue
        table = Base.metadata.tables[table_name]
        cursor.execute(f"PRAGMA table_info({table_name});")
        db_cols = {row[1]: {"type": row[2], "notnull": row[3], "pk": row[5]} for row in cursor.fetchall()}
        model_cols = set(table.columns.keys())
        
        missing = model_cols - set(db_cols.keys())
        if missing:
            all_columns_synced = False
            print(f"   [X] Bảng '{table_name}': THIẾU CỘT TRONG DB -> {missing}")
        else:
            print(f"   [V] Bảng '{table_name}': Đủ {len(model_cols)}/{len(model_cols)} cột.")

    conn.close()
    
    print("\n==================================================")
    if not missing_tables and all_columns_synced and integrity[0][0] == "ok" and not fk_violations:
        print("   KẾT LUẬN: CƠ SỞ DỮ LIỆU ĐỒNG BỘ HOÀN TOÀN 100%!")
        print("==================================================")
        return True
    else:
        print("   KẾT LUẬN: PHÁT HIỆN LỆCH SCHEMA / DỮ LIỆU CẦN ĐỒNG BỘ!")
        print("==================================================")
        return False

if __name__ == "__main__":
    verify_db_sync()
