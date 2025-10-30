import logging
import traceback
from typing import Optional, Callable
from PyQt6.QtWidgets import QMessageBox, QWidget
from functools import wraps

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, message: str, user_message: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message
        self.details = details


class DatabaseException(AppException):
    pass


class ValidationException(AppException):
    pass


class FileException(AppException):
    pass


def show_error_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if details:
        msg_box.setDetailedText(details)
    
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def show_warning_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str
):
    QMessageBox.warning(parent, title, message)


def show_info_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str
):
    QMessageBox.information(parent, title, message)


def handle_exception(
    exception: Exception,
    parent: Optional[QWidget] = None,
    user_message: Optional[str] = None,
    log_error: bool = True
) -> None:
    if log_error:
        logger.error(f"Exception occurred: {str(exception)}", exc_info=True)
    if isinstance(exception, AppException):
        display_message = exception.user_message
        details = exception.details
    elif user_message:
        display_message = user_message
        details = str(exception)
    else:
        display_message = "Bir hata oluştu. Lütfen tekrar deneyin."
        details = str(exception)
    if parent:
        show_error_dialog(
            parent,
            "Hata",
            display_message,
            details=f"{type(exception).__name__}: {details}\n\nDetaylı log dosyasında mevcut."
        )


def safe_execute(
    func: Callable,
    parent: Optional[QWidget] = None,
    error_message: Optional[str] = None,
    default_return=None
):
    try:
        return func()
    except Exception as e:
        handle_exception(e, parent, error_message)
        return default_return


def exception_handler(user_message: Optional[str] = None, reraise: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                parent = args[0] if args and isinstance(args[0], QWidget) else None
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                handle_exception(e, parent, user_message, log_error=False)
                if reraise:
                    raise
                return None
        return wrapper
    return decorator


def validate_input(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    required: bool = True
) -> None:
    if required and not value.strip():
        raise ValidationException(
            f"{field_name} alanı boş bırakılamaz",
            user_message=f"⚠️ {field_name} alanı zorunludur"
        )
    
    if min_length and len(value) < min_length:
        raise ValidationException(
            f"{field_name} en az {min_length} karakter olmalıdır",
            user_message=f"⚠️ {field_name} en az {min_length} karakter olmalıdır"
        )
    
    if max_length and len(value) > max_length:
        raise ValidationException(
            f"{field_name} en fazla {max_length} karakter olabilir",
            user_message=f"⚠️ {field_name} en fazla {max_length} karakter olabilir"
        )


def validate_number(
    value,
    field_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> None:
    try:
        num_value = float(value) if not isinstance(value, (int, float)) else value
    except (ValueError, TypeError):
        raise ValidationException(
            f"{field_name} sayısal bir değer olmalıdır",
            user_message=f"⚠️ {field_name} geçerli bir sayı olmalıdır"
        )
    
    if min_value is not None and num_value < min_value:
        raise ValidationException(
            f"{field_name} en az {min_value} olmalıdır",
            user_message=f"⚠️ {field_name} en az {min_value} olmalıdır"
        )
    
    if max_value is not None and num_value > max_value:
        raise ValidationException(
            f"{field_name} en fazla {max_value} olabilir",
            user_message=f"⚠️ {field_name} en fazla {max_value} olabilir"
        )


def log_operation(operation_name: str, success: bool = True, details: Optional[str] = None):
    if success:
        msg = f"✓ {operation_name} başarılı"
        if details:
            msg += f" - {details}"
        logger.info(msg)
    else:
        msg = f"✗ {operation_name} başarısız"
        if details:
            msg += f" - {details}"
        logger.error(msg)
