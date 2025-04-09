# (DEPRECATED) Modpack Installer for Lethal Company

I created this to make it easy for friends to install and uninstall mods for Lethal Company

## File Info

Many Files are not included like the main exe and pkg for size purposes

Also not included is the credentials.json becuase duh, you can't have my keys!

The mod files and bepin files are here but the program uses GoogleDriveAPI to get them from the cloud.

The music for the Boombox Mod is also not in here, put your own if you want.

## Instructions to repackage with differenet mods
1. In the main python code there are two lines that consist of the fileID of both zips in Google Drive. You would need to change those to whatever your fileID is.
2. You would also need a credentials.json from the GoogleDriveAPI
3. Using pyinstaller, you would need to run this command: 
pyinstaller --onefile --windowed --icon=app_icon.ico --add-data "dark_mode.qss;." --add-data "credentials.json;." modpack_installer.py
4. this will output a dist folder that has the exe installer.

### Author

Paksh Patel
