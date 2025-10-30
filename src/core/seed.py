from argon2 import PasswordHasher
from src.core.db_raw import get_db
from src.utils.logger import logger

ph = PasswordHasher()


def seed_departments():
    db = get_db()
    
    departments_data = [
        {"code": "BLM", "name": "Bilgisayar Mühendisliği"},
        {"code": "YZM", "name": "Yazılım Mühendisliği"},
        {"code": "ELK", "name": "Elektrik Mühendisliği"},
        {"code": "ELT", "name": "Elektronik Mühendisliği"},
        {"code": "INS", "name": "İnşaat Mühendisliği"},
    ]
    
    department_ids = []
    for dept_data in departments_data:
        existing = db.fetch_one(
            "SELECT id FROM departments WHERE code = ?",
            (dept_data["code"],)
        )
        
        if not existing:
            dept_id = db.execute(
                "INSERT INTO departments (code, name, is_active) VALUES (?, ?, 1)",
                (dept_data["code"], dept_data["name"])
            )
            department_ids.append(dept_id)
            logger.info(f"  ✓ Bölüm eklendi: {dept_data['name']}")
        else:
            department_ids.append(existing['id'])
            logger.info(f"  ⊙ Bölüm zaten var: {dept_data['name']}")
    
    return department_ids


def seed_admin_user():
    db = get_db()
    
    admin_email = "admin@exam.com"
    admin_password = "admin123"
    
    existing = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        (admin_email,)
    )
    
    if not existing:
        db.execute(
            """INSERT INTO users 
               (email, password_hash, full_name, role, is_active, department_id) 
               VALUES (?, ?, ?, ?, 1, NULL)""",
            (admin_email, ph.hash(admin_password), "Sistem Yöneticisi", "admin")
        )
        logger.info(f"  ✓ Admin kullanıcı oluşturuldu: {admin_email}")
        logger.info(f"    Şifre: {admin_password} (lütfen değiştirin!)")
    else:
        logger.info(f"  ⊙ Admin kullanıcı zaten var: {admin_email}")


def seed_coordinators(department_ids):
    db = get_db()
    
    departments = db.fetch_all("SELECT id, code, name FROM departments")
    
    for dept in departments:
        coord_email = f"koordinator.{dept['code'].lower()}@exam.com"
        coord_password = f"{dept['code'].lower()}123"
        
        existing = db.fetch_one(
            "SELECT id FROM users WHERE email = ?",
            (coord_email,)
        )
        
        if not existing:
            db.execute(
                """INSERT INTO users 
                   (email, password_hash, full_name, role, is_active, department_id) 
                   VALUES (?, ?, ?, 'coordinator', 1, ?)""",
                (coord_email, ph.hash(coord_password), 
                 f"{dept['name']} Koordinatörü", dept['id'])
            )
            logger.info(f"  ✓ Koordinatör oluşturuldu: {coord_email} (şifre: {coord_password})")
        else:
            logger.info(f"  ⊙ Koordinatör zaten var: {coord_email}")


def seed_classrooms(department_ids):
    db = get_db()
    
    classroom_configs = [
        {"code": "D201", "capacity": 60, "rows": 10, "columns": 6, "seating": 2},
        {"code": "D202", "capacity": 90, "rows": 10, "columns": 9, "seating": 3},
        {"code": "D203", "capacity": 40, "rows": 10, "columns": 4, "seating": 2},
        {"code": "A101", "capacity": 100, "rows": 10, "columns": 10, "seating": 2},
        {"code": "B105", "capacity": 30, "rows": 15, "columns": 2, "seating": 2},
        {"code": "C301", "capacity": 30, "rows": 10, "columns": 3, "seating": 3},
    ]
    
    departments = db.fetch_all("SELECT id, code FROM departments")
    
    for dept in departments:
        for config in classroom_configs:
            classroom_code = f"{dept['code']}-{config['code']}"
            
            existing = db.fetch_one(
                "SELECT id FROM classrooms WHERE code = ?",
                (classroom_code,)
            )
            
            if not existing:
                db.execute(
                    """INSERT INTO classrooms 
                       (code, department_id, capacity, rows, columns, seating_arrangement, is_active) 
                       VALUES (?, ?, ?, ?, ?, ?, 1)""",
                    (classroom_code, dept['id'], config['capacity'], 
                     config['rows'], config['columns'], config['seating'])
                )
                logger.info(f"    ✓ Derslik eklendi: {classroom_code} ({config['columns']} sütun, kapasite: {config['capacity']})")
            else:
                logger.info(f"    ⊙ Derslik zaten var: {classroom_code}")


def run_seed():
    logger.info("=" * 60)
    logger.info("🌱 Veritabanı tohum verileri ekleniyor...")
    logger.info("=" * 60)
    
    from src.core.db_raw import init_db_raw
    db = init_db_raw()
    
    try:
        logger.info("\n1️⃣ Bölümler ekleniyor...")
        department_ids = seed_departments()
        
        logger.info("\n2️⃣ Admin kullanıcı ekleniyor...")
        seed_admin_user()
        
        logger.info("\n3️⃣ Koordinatör kullanıcılar ekleniyor...")
        seed_coordinators(department_ids)
        
        logger.info("\n4️⃣ Derslikler ekleniyor...")
        seed_classrooms(department_ids)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Tohum verileri başarıyla eklendi!")
        logger.info("=" * 60)
        
        logger.info("\n📊 ÖZET:")
        logger.info(f"  • Bölüm sayısı: {len(db.fetch_all('SELECT * FROM departments'))}")
        logger.info(f"  • Kullanıcı sayısı: {len(db.fetch_all('SELECT * FROM users'))}")
        logger.info(f"  • Derslik sayısı: {len(db.fetch_all('SELECT * FROM classrooms'))}")
        
        logger.info("\n🔐 GİRİŞ BİLGİLERİ:")
        logger.info("  Admin:")
        logger.info("    E-posta: admin@exam.com")
        logger.info("    Şifre: admin123")
        logger.info("\n  Koordinatörler:")
        
        departments = db.fetch_all("SELECT code, name FROM departments ORDER BY code")
        for dept in departments:
            logger.info(f"    {dept['name']}:")
            logger.info(f"      E-posta: koordinator.{dept['code'].lower()}@exam.com")
            logger.info(f"      Şifre: {dept['code'].lower()}123")
        
    except Exception as e:
        logger.error(f"❌ Tohum verileri eklenirken hata: {e}")
        raise


if __name__ == "__main__":
    run_seed()
