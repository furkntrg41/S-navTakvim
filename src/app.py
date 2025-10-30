import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.ui.login_window import LoginWindow
from src.core.db_raw import Database
from src.utils.logger import logger
from src.config import APP_NAME, APP_VERSION


def exception_hook(exctype, value, traceback):
    logger.error("Yakalanmayan hata!", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)


def main():
    sys.excepthook = exception_hook
    logger.info(f"🚀 {APP_NAME} v{APP_VERSION} başlatılıyor...")

    try:
        db = Database()
        db.create_tables()
        logger.info("✓ Veritabanı başlatıldı (RAW SQL)")
    except Exception as e:
        logger.error(f"✗ Veritabanı hatası: {e}")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    main_window = None
    login_window = None
    restart_requested = True

    while restart_requested:
        restart_requested = False

        def request_restart():
            nonlocal restart_requested
            restart_requested = True
            if main_window:
                main_window.close()

        def show_main_window(user):
            nonlocal main_window
            logger.info(f"✓ Kullanıcı girişi: {user['email']} ({user['role']})")

            main_window = MainWindow(user=user, restart_callback=request_restart)
            main_window.show()
            logger.info("✓ Ana Arayüz Başlatıldı")

            app.exec()

        login_window = LoginWindow()
        login_window.login_successful.connect(show_main_window)
        login_window.show()

        app.exec()

    logger.info("Uygulama kapatıldı")
    sys.exit(0)


if __name__ == "__main__":
    main()
