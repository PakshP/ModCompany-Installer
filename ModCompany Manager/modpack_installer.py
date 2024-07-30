import os
import shutil
import sys
import zipfile
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent, QIcon

# Google Drive file IDs for ZIP files
BEPINEX_ZIP_ID = '1uaFe7VEqf0uKGmALyBHO_Ay_Kx4qGey8'
MODS_ZIP_ID = '1qf_egaOp5JJysxwQC5yHQWb0R58zIjX7'

# Function to get the absolute path to a resource, works for both development and PyInstaller
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Authenticate and initialize Google Drive API
def authenticate_google_drive():
    creds_path = resource_path('credentials.json')
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)
    return service

def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {file_id}: {int(status.progress() * 100)}%")

def download_and_extract_zip(service, file_id, dest_dir):
    zip_path = os.path.join(dest_dir, 'temp.zip')
    download_file(service, file_id, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)
    os.remove(zip_path)

class CustomTitleBar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setObjectName("TitleBar")
        self.setStyleSheet("""
            #TitleBar {
                background-color: #2e2e2e;
                color: #f0f0f0;
                border-bottom: 1px solid #5e5e5e;
            }
            QLabel {
                padding-left: 5px;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #f0f0f0;
                border: none;
            }
            QPushButton:hover {
                background-color: #5e5e5e;
            }
        """)

        self.setFixedHeight(30)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title = QLabel(self.parent.windowTitle(), self)
        layout.addWidget(self.title)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(spacer)

        self.closeButton = QPushButton('X', self)
        self.closeButton.setFixedSize(30, 30)
        self.closeButton.clicked.connect(self.parent.close)
        layout.addWidget(self.closeButton)

        self.setLayout(layout)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.parent.dragPos = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.parent.move(self.parent.pos() + event.globalPos() - self.parent.dragPos)
            self.parent.dragPos = event.globalPos()
            event.accept()

class ModpackInstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.dragPos = QPoint()
        self.service = authenticate_google_drive()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle('Modpack Installer')
        self.setGeometry(100, 100, 500, 600)

        # Set the window icon
        icon_path = resource_path('app_icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.titleBar = CustomTitleBar(self)
        layout.addWidget(self.titleBar)

        contentLayout = QVBoxLayout()
        contentLayout.setContentsMargins(20, 20, 20, 20)
        contentLayout.setSpacing(10)

        # Step 1
        self.step1_label = QLabel('Step 1: Select the game directory', self)
        contentLayout.addWidget(self.step1_label)
        self.game_dir_input = QLineEdit(self)
        contentLayout.addWidget(self.game_dir_input)
        self.browse_button = QPushButton('Browse', self)
        self.browse_button.clicked.connect(self.select_game_directory)
        contentLayout.addWidget(self.browse_button)

        # Step 2
        self.step2_label = QLabel('Step 2: Install BepInEx', self)
        contentLayout.addWidget(self.step2_label)
        self.notice_label = QLabel('If you already have it installed, don\'t worry about it and skip to Step 4', self)
        contentLayout.addWidget(self.notice_label)
        self.install_bepinex_button = QPushButton('Install BepInEx', self)
        self.install_bepinex_button.clicked.connect(self.install_bepinex)
        contentLayout.addWidget(self.install_bepinex_button)

        # Step 3
        self.step3_label = QLabel('Step 3: IMPORTANT !!! RUN GAME TO THE MAIN MENU THEN CLOSE IT', self)
        contentLayout.addWidget(self.step3_label)

        # Step 4
        self.step4_label = QLabel('Step 4: Install Mods and Files', self)
        contentLayout.addWidget(self.step4_label)
        self.install_mods_button = QPushButton('Install Mods and Files', self)
        self.install_mods_button.clicked.connect(self.install_modpack)
        contentLayout.addWidget(self.install_mods_button)

        # Step 5
        self.step5_label = QLabel("Step 5: Don't complain to Pux when it doesn't work (complain to Nicholas)", self)
        contentLayout.addWidget(self.step5_label)

        # Uninstall Section
        self.uninstall_label = QLabel('Uninstall all mods and BepInEx', self)
        contentLayout.addWidget(self.uninstall_label)
        self.uninstall_button = QPushButton('Uninstall', self)
        self.uninstall_button.clicked.connect(self.uninstall_mods)
        contentLayout.addWidget(self.uninstall_button)

        layout.addLayout(contentLayout)
        self.setLayout(layout)

        # Load dark mode stylesheet
        self.load_stylesheet()

    def load_stylesheet(self):
        qss_path = resource_path('dark_mode.qss')
        with open(qss_path, 'r') as f:
            self.setStyleSheet(f.read())

    def select_game_directory(self):
        game_dir = QFileDialog.getExistingDirectory(self, 'Select Game Directory')
        self.game_dir_input.setText(game_dir)

    def install_bepinex(self):
        game_dir = self.game_dir_input.text()
        if not game_dir:
            QMessageBox.critical(self, 'Error', 'Please select the game directory')
            return

        # Check if BepInEx is already installed
        bepinex_dir = os.path.join(game_dir, "BepInEx")
        if os.path.exists(bepinex_dir):
            QMessageBox.information(self, 'BepInEx Installed', 'BepInEx is already installed. You don\'t need to reinstall it.')
            return

        # Download and extract BepInEx files
        try:
            download_and_extract_zip(self.service, BEPINEX_ZIP_ID, game_dir)
            QMessageBox.information(self, 'Success', 'BepInEx installed successfully. Now run the game to the main menu and then close it.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to install BepInEx: {e}')

    def install_modpack(self):
        game_dir = self.game_dir_input.text()
        if not game_dir:
            QMessageBox.critical(self, 'Error', 'Please select the game directory')
            return

        # Specific folders to copy into the BepInEx directory
        bepinex_dir = os.path.join(game_dir, "BepInEx")
        if not os.path.exists(bepinex_dir):
            QMessageBox.critical(self, 'Error', f'BepInEx directory does not exist in the game directory: {bepinex_dir}')
            return

        # Download and extract mod files
        try:
            download_and_extract_zip(self.service, MODS_ZIP_ID, bepinex_dir)
            QMessageBox.information(self, 'Success', 'Modpack installed successfully. Don\'t complain to Pux when it doesn\'t work (complain to Nicholas).')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to install mods: {e}')

    def uninstall_mods(self):
        game_dir = self.game_dir_input.text()
        if not game_dir:
            QMessageBox.critical(self, 'Error', 'Please select the game directory')
            return

        bepinex_dir = os.path.join(game_dir, "BepInEx")
        files_to_delete = ["doorstop_config.ini", "winhttp.dll"]

        # Remove BepInEx directory
        if os.path.exists(bepinex_dir):
            try:
                shutil.rmtree(bepinex_dir)
                print(f"Deleted {bepinex_dir}")
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to delete {bepinex_dir}: {e}')
                return

        # Remove specific files
        for file in files_to_delete:
            file_path = os.path.join(game_dir, file)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to delete {file_path}: {e}')
                    return

        QMessageBox.information(self, 'Success', 'All mods and BepInEx have been uninstalled successfully.')

def main():
    app = QApplication(sys.argv)
    ex = ModpackInstaller()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
