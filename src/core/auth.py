from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from src.core.db_raw import get_db
from src.utils.logger import logger


ph = PasswordHasher()


def authenticate_user(email: str, password: str):
    db = get_db()
    
    try:
        user = db.fetch_one(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email,)
        )
        
        if not user:
            logger.warning(f"❌ Başarısız giriş: {email}")
            return None
        
        try:
            ph.verify(user['password_hash'], password)
            logger.info(f"✓ Başarılı giriş: {email} ({user['role']})")
            
            if ph.check_needs_rehash(user['password_hash']):
                new_hash = ph.hash(password)
                db.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (new_hash, user['id'])
                )
            
            return dict(user)
            
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            logger.warning(f"❌ Hatalı şifre: {email}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Kimlik doğrulama hatası: {e}")
        return None


def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
    db = get_db()
    
    try:
        user = db.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not user:
            return False, "Kullanıcı bulunamadı!"
        
        try:
            ph.verify(user['password_hash'], old_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            logger.warning(f"❌ Şifre değiştirme başarısız - Hatalı mevcut şifre: {user['email']}")
            return False, "Mevcut şifre hatalı!"
        
        if len(new_password) < 6:
            return False, "Yeni şifre en az 6 karakter olmalıdır!"
        
        new_hash = ph.hash(new_password)
        db.execute(
            "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_hash, user_id)
        )
        
        logger.info(f"✓ Şifre değiştirildi: {user['email']}")
        return True, "Şifre başarıyla değiştirildi!"
        
    except Exception as e:
        logger.error(f"❌ Şifre değiştirme hatası: {e}")
        return False, f"Hata: {str(e)}"


def check_permission(user, required_role: str = None) -> bool:
    if not user:
        return False
    
    if user['role'] == 'admin':
        return True
    
    if required_role:
        return user['role'] == required_role
    
    return True


def can_access_department(user, department_id: int) -> bool:
    if not user:
        return False
    
    if user['role'] == 'admin':
        return True
    
    if user['role'] == 'coordinator':
        return user['department_id'] == department_id
    
    return False
