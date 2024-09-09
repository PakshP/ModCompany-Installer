import os
import shutil
import sys
import zipfile
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox, 
                             QHBoxLayout, QFrame, QSpacerItem, QSizePolicy, 
                             QMainWindow, QGridLayout, QCheckBox, QListWidgetItem,
                             QSplitter, QListWidget)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon

# Google Drive file IDs for BepInEx ZIP files 
BEPINEX_ZIP_ID = '1uaFe7VEqf0uKGmALyBHO_Ay_Kx4qGey8'

# Function to get the absolute path to a resource
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Authenticate and initialize Google Drive API
def authenticate_google_drive():
    creds_path = resource_path('credentials.json')
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)
    return service

# Download and extract BepInEx
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent.dragPos = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.parent.move(self.parent.pos() + event.globalPos() - self.parent.dragPos)
            self.parent.dragPos = event.globalPos()
            event.accept()

MODS_PER_PAGE = 18  # 18 mods per page
COLUMNS = 3  # 3 columns per row

class ModSelectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Mods")
        self.setGeometry(100, 100, 1000, 600)  # Larger window for better UI experience
        self.selected_mods = []  # Track selected mods
        self.dependencies = {}   # Track mod dependencies
        self.current_page = 0  # Page tracker
        self.mods = []  # Full list of mods
        self.filtered_mods = []  # Filtered mods after search
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search for mods and press Enter...")
        self.search_bar.returnPressed.connect(self.filter_mods)  # Search only on Enter
        layout.addWidget(self.search_bar)

        # Splitter for grid layout and selected mods section
        splitter = QSplitter(self)
        layout.addWidget(splitter)

        # Grid layout for mod list
        self.grid_widget = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)

        # List widget for selected mods
        self.selected_mods_widget = QListWidget(self)
        splitter.addWidget(self.grid_widget)
        splitter.addWidget(self.selected_mods_widget)
        splitter.setSizes([700, 300])  # Set sizes for grid and selected mods section

        # Pagination buttons
        pagination_layout = QVBoxLayout()
        self.prev_button = QPushButton("Previous", self)
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.next_button)
        layout.addLayout(pagination_layout)

        # Confirm button to proceed with the selected mods
        self.confirm_button = QPushButton("Install Selected Mods", self)
        self.confirm_button.clicked.connect(self.confirm_selection)
        layout.addWidget(self.confirm_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Load mods from Thunderstore
        self.load_mods_from_thunderstore()

    def load_mods_from_thunderstore(self):
        try:
            # Thunderstore API endpoint for Lethal Company
            response = requests.get("https://thunderstore.io/c/lethal-company/api/v1/package/", timeout=10)
            self.mods = response.json()

            # Store dependencies for each mod
            for mod in self.mods:
                mod_name = mod['name']
                dependencies = mod['versions'][0].get('dependencies', [])
                self.dependencies[mod_name] = dependencies

            # Initialize filtered mods and show the first page
            self.filtered_mods = self.mods
            self.show_page(0)
        except requests.Timeout:
            QMessageBox.critical(self, "Error", "Connection to Thunderstore timed out. Please try again later.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load mods: {e}")

    def show_page(self, page_num):
        self.grid_layout.setSpacing(10)
        # Clear the grid layout
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Calculate start and end index for mods to display
        start_idx = page_num * MODS_PER_PAGE
        end_idx = min(start_idx + MODS_PER_PAGE, len(self.filtered_mods))

        row, col = 0, 0
        for mod in self.filtered_mods[start_idx:end_idx]:
            mod_name = mod['name']
            mod_version = mod['versions'][0]['version_number']

            # Create a checkbox for each mod
            mod_checkbox = QCheckBox(f"{mod_name} - v{mod_version}")
            mod_checkbox.stateChanged.connect(lambda state, mod=mod: self.select_mod(mod, state))
            self.grid_layout.addWidget(mod_checkbox, row, col)

            col += 1
            if col == COLUMNS:  # 3 items per row
                col = 0
                row += 1

        # Update current page
        self.current_page = page_num
        self.update_pagination_buttons()

    def update_pagination_buttons(self):
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled((self.current_page + 1) * MODS_PER_PAGE < len(self.filtered_mods))

    def prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def next_page(self):
        if (self.current_page + 1) * MODS_PER_PAGE < len(self.filtered_mods):
            self.show_page(self.current_page + 1)

    def select_mod(self, mod, state):
        mod_name = mod['name']
        if state == Qt.Checked:
            self.selected_mods.append(mod)
            self.selected_mods_widget.addItem(QListWidgetItem(f"{mod_name}"))
        else:
            self.selected_mods = [m for m in self.selected_mods if m['name'] != mod_name]
            # Remove from selected mods widget
            items = self.selected_mods_widget.findItems(mod_name, Qt.MatchExactly)
            if items:
                self.selected_mods_widget.takeItem(self.selected_mods_widget.row(items[0]))

    def filter_mods(self):
        search_text = self.search_bar.text().lower()
        self.filtered_mods = [mod for mod in self.mods if search_text in mod['name'].lower()]
        self.show_page(0)

    def confirm_selection(self):
        missing_dependencies = []
        for mod in self.selected_mods:
            mod_name = mod['name']
            dependencies = self.dependencies.get(mod_name, [])
            if dependencies:
                missing_dependencies.append((mod_name, dependencies))

        if missing_dependencies:
            self.ask_for_dependencies(missing_dependencies)
        else:
            self.proceed_with_installation()

    def ask_for_dependencies(self, missing_dependencies):
        dep_message = "Some mods have missing dependencies:\n\n"
        for mod_name, dependencies in missing_dependencies:
            dep_message += f"{mod_name} depends on: {', '.join(dependencies)}\n"
        dep_message += "\nWould you like to auto-install the dependencies?"

        reply = QMessageBox.question(self, 'Dependencies Found', dep_message, 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.auto_install_dependencies(missing_dependencies)
        else:
            self.proceed_with_installation()

    def auto_install_dependencies(self, missing_dependencies):
        for mod_name, dependencies in missing_dependencies:
            for dependency in dependencies:
                # Assuming dependencies can be found in the mods list
                dependency_mod = next((mod for mod in self.mods if mod['name'] == dependency), None)
                if dependency_mod and dependency_mod not in self.selected_mods:
                    self.selected_mods.append(dependency_mod)
                    self.selected_mods_widget.addItem(QListWidgetItem(f"{dependency_mod['name']}"))

        self.proceed_with_installation()

    def proceed_with_installation(self):
        game_dir = self.parent().game_dir_input.text()  # Get game directory from main window
        if not game_dir:
            QMessageBox.critical(self, 'Error', 'Please select the game directory')
            return
        
        try:
            for mod in self.selected_mods:
                mod_name = mod['name']
                mod_version = mod['versions'][0]['version_number']
                download_url = mod['versions'][0]['download_url']

                # Download the mod file
                mod_zip_path = os.path.join(game_dir, f"{mod_name}.zip")
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()  # Check if the download was successful
                    with open(mod_zip_path, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)

                # Extract mod files to the BepInEx plugins folder
                bepinex_plugins_dir = os.path.join(game_dir, 'BepInEx', 'plugins')
                with zipfile.ZipFile(mod_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(bepinex_plugins_dir)

                # Clean up zip file
                os.remove(mod_zip_path)

            QMessageBox.information(self, 'Success', 'Mods installed successfully.')

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, 'Download Error', f'Failed to download mods: {e}')
        except zipfile.BadZipFile as e:
            QMessageBox.critical(self, 'Zip Error', f'Failed to extract mod files: {e}')
        except Exception as e:
            QMessageBox.critical(self, 'Installation Error', f'An unexpected error occurred: {e}')

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

        # Step 2: Install BepInEx
        self.step2_label = QLabel('Step 2: Install BepInEx', self)
        contentLayout.addWidget(self.step2_label)
        self.install_bepinex_button = QPushButton('Install BepInEx', self)
        self.install_bepinex_button.clicked.connect(self.install_bepinex)
        contentLayout.addWidget(self.install_bepinex_button)

        # Step 4: New button for selecting mods
        self.step4_label = QLabel('Step 4: Select and Install Mods', self)
        contentLayout.addWidget(self.step4_label)
        self.select_mods_button = QPushButton('Select Mods', self)
        self.select_mods_button.clicked.connect(self.open_mod_selection_window)
        contentLayout.addWidget(self.select_mods_button)

        # Uninstall section
        self.uninstall_label = QLabel('Uninstall all mods and BepInEx', self)
        contentLayout.addWidget(self.uninstall_label)
        self.uninstall_button = QPushButton('Uninstall', self)
        self.uninstall_button.clicked.connect(self.uninstall_mods)
        contentLayout.addWidget(self.uninstall_button)

        layout.addLayout(contentLayout)
        self.setLayout(layout)

    def open_mod_selection_window(self):
        self.mod_selection_window = ModSelectionWindow()
        self.mod_selection_window.show()

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
            QMessageBox.information(self, 'BepInEx Installed', 'BepInEx is already installed.')
            return

        try:
            download_and_extract_zip(self.service, BEPINEX_ZIP_ID, game_dir)
            QMessageBox.information(self, 'Success', 'BepInEx installed successfully. Now run the game to the main menu and then close it.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to install BepInEx: {e}')

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
