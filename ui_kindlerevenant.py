# this Python file uses the following encoding: utf-8
from ui_form import Ui_Ui_KindleRevenant
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTableWidget,
    QApplication,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QHeaderView,
    QFileDialog,
    QAbstractItemView,
    QToolBar,
    QLabel,
    QMessageBox,
    QStatusBar,
    QToolButton,
    QMenu,
    QWidgetAction,
)
from PySide6.QtCore import QTimer

import os
import shutil
from datetime import datetime
import sqlite3
import pathlib
import sys
import requests
import json
import time

# only works for windows
# find alternatives for linux & macos
if sys.platform == "win32":
    import win32api
    import win32file

# default file locations
KINDLE_DB_LOCATION = ""
NEW_DB = "revenant.db"
ANKI_FILE_DIRECTORY = r"%APPDATA%\Anki2"
COLUMNS = ["Word", "Stem", "Category", "Date", "Frequency", "Definition"]


class Ui_KindleRevenant(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Ui_KindleRevenant()
        self.ui.setupUi(self)

        self.setWindowTitle("My App")
        self.setMinimumSize(500, 500)

        self.dbCon = None

        layout = QVBoxLayout()
        buttonLayout = QHBoxLayout()

        self.createDisplayTable(layout)

        print(os.path.exists(os.path.join(pathlib.Path().resolve(), NEW_DB)))
        print(os.path.join(pathlib.Path().resolve(), NEW_DB))
        print(os.path.isfile(NEW_DB))

        if (os.path.exists(NEW_DB)):
            self.displayTable()
        self.showButtons(buttonLayout)
        kindleConnectedLabel = self._ToolBar()

        layout.addLayout(buttonLayout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.setStatusBar(QStatusBar(self))

        print(os.path.isfile(NEW_DB))
        self.timer = QTimer()
        self.timer.timeout.connect(
            lambda label=kindleConnectedLabel:
            self.changeKindleConnectedMessage(label)
        )
        self.timer.start(5000)

    def selectDbLocationClicked(self):
        global KINDLE_DB_LOCATION
        KINDLE_DB_LOCATION = QFileDialog.getOpenFileName(
            self, "Open Kindle DB Location",
            pathlib.Path().resolve().__str__(),
            'SQLite DB (*.db)'
        )[0]

    def syncKindleClicked(self):
        global KINDLE_DB_LOCATION
        if not KINDLE_DB_LOCATION and self.kindleConnected()[0]:
            KINDLE_DB_LOCATION = self.getKindleDBPath()
            self.mergeDatabases()
            self.displayTable()
        elif KINDLE_DB_LOCATION:
            print(os.path.isfile(NEW_DB))
            self.mergeDatabases()
            self.displayTable()
        else:
            QMessageBox().warning(
                None,
                "Warning",
                """
                Please ensure the kindle is connected.
                Alternatively you can specify the database location manually.
                """
            )

    def exportClicked(self):
        print(pathlib.Path().resolve().__str__())
        exportLocation = QFileDialog.getSaveFileName(
            self, "Export DB Location",
            pathlib.Path().resolve().__str__(),
            'Tab Seperated txt(*.txt)'
        )[0]
        self.exportDatabase(exportLocation)

    def ankiLocationClicked(self):
        global ANKI_FILE_DIRECTORY
        ANKI_FILE_DIRECTORY = QFileDialog.getOpenFileName(
            self, "Open Kindle DB Location",
            os.path.expandvars(ANKI_FILE_DIRECTORY),
            'SQLite DB (*.db)')[0]

    def scrapeOptionClicked(self):
        words = self.getNumberRows()
        wordsCompleted = 0
        numScrapedSuccesfully = 0

        progressMessage = QLabel("Scraping Definitions: "
                                 f"{wordsCompleted}/{words}")
        self.statusBar().addWidget(progressMessage)

        self.openDatabase()

        query = QSqlQuery("SELECT id, stem, definition  FROM WORDS")
        insertionQuery = QSqlQuery()

        while query.next():
            wordsCompleted += 1
            progressMessage.setText("Scraping Definitions: "
                                    f"{wordsCompleted}/{words}")

            word_id = query.value(0)
            word_stem = query.value(1)
            existingDef = query.value(2)

            if not existingDef:
                definition = self.scrapeWordDefinition(word_stem)
                while definition == "cloudflare":
                    time.sleep(10)
                    definition = self.scrapeWordDefinition(word_stem)
            else:
                definition = ""

            if definition:
                self.dbCon.transaction()
                insertionQuery.prepare("UPDATE WORDS SET "
                                       "definition=:definition "
                                       "WHERE id=:wordID")
                insertionQuery.bindValue(":definition", definition)
                insertionQuery.bindValue(":wordID", word_id)
                insertionQuery.exec()
                numScrapedSuccesfully += 1

        QMessageBox.information(
            None,
            "Success",
            f"{numScrapedSuccesfully} definitions were successfully added."
        )

        self.dbCon.commit()
        self.closeDatabase()
        self.displayTable()

    def changeKindleConnectedMessage(self, kindleConnectedLabel):
        if self.kindleConnected()[0]:
            kindleConnectedLabel.setText("Kindle Connected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold;"
                                               "text-align:left;"
                                               "color: green;")
        else:
            kindleConnectedLabel.setText("Kindle Disconnected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold;"
                                               "text-align:left;"
                                               "color: grey;")

    def _ToolBar(self):
        if self.kindleConnected()[0]:
            kindleConnectedLabel = QLabel("Kindle Connected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold;"
                                               "text-align:left;"
                                               "color: green;")
        else:
            kindleConnectedLabel = QLabel("Kindle Disconnected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold;"
                                               "text-align:left;"
                                               "color: grey;")

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        scrapeOption = QAction("Add Definitions", self)
        scrapeOption.setStatusTip(
            "Add definitions to all the cards in database.")
        scrapeOption.triggered.connect(self.scrapeOptionClicked)

        toolButton = QToolButton()
        toolButton.setText("Options")

        optionsMenu = QMenu(toolButton)
        optionsMenu.addAction(scrapeOption)
        toolButton.setMenu(optionsMenu)

        toolButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        toolButtonAction = QWidgetAction(self)
        toolButtonAction.setDefaultWidget(toolButton)

        toolbar.addAction(toolButtonAction)
        toolbar.addWidget(kindleConnectedLabel)

        return kindleConnectedLabel

    def mergeDatabases(self):
        #  a copy of the existing kindle vocab.db if revenant.db doesn't exist
        print("The kindle location is "
              f"{KINDLE_DB_LOCATION}"
              f"{str(os.path.isfile(KINDLE_DB_LOCATION))}")
        if not KINDLE_DB_LOCATION:
            QMessageBox.warning(
                None,
                "Error",
                "The Kindle DB was not found "
                "or its location has not been specified."
            )
        elif not os.path.isfile(KINDLE_DB_LOCATION):
            QMessageBox.warning(
                None,
                "Error",
                f"The specified kindle db location "
                f"{KINDLE_DB_LOCATION} does not exist"
            )
        elif not NEW_DB:
            QMessageBox.warning(
                None,
                "Error",
                "The export location has not been set"
            )
        elif not os.path.isfile(NEW_DB):
            shutil.copyfile(KINDLE_DB_LOCATION, NEW_DB)
            self.openDatabase()

            self.createNewColumns()

            self.closeDatabase()

            numWords = self.getNumberRows()

            QMessageBox.information(
                None,
                "Information",
                (f"A new Kindle Revenant DB has been created at {NEW_DB}"
                 f".\n{numWords} words were successfully imported.")
            )
        else:
            # if both files exist merge the tables from the old & new db
            currentWords = self.getNumberRows()
            self.copyTables(NEW_DB)
            newNumberWords = self.getNumberRows()
            numWords = newNumberWords - currentWords

            QMessageBox.information(
                None,
                "Information",
                (f"{numWords} words were successfully imported "
                 "from the following location:"
                 f"\n{KINDLE_DB_LOCATION}")
            )

    @staticmethod
    def copyTables(dbToCopy):
        db = sqlite3.connect(dbToCopy)
        db_cursor = db.cursor()

        db_cursor.execute(f"ATTACH DATABASE '{KINDLE_DB_LOCATION}' as 'Y'")

        tables_to_copy = ["BOOK_INFO", "DICT_INFO",
                          "LOOKUPS", "METADATA",
                          "VERSION"]

        for table in tables_to_copy:
            db_cursor.execute(f"INSERT OR IGNORE INTO {table}"
                              f" SELECT * FROM Y.{table};")
        db_cursor.execute("INSERT OR IGNORE INTO WORDS"
                          "(id, word, stem, lang, category, "
                          "timestamp, profileid)"
                          "SELECT id, word, stem, lang, category, "
                          "timestamp, profileid "
                          "FROM Y.WORDS;")

        db.commit()
        db.close()

        if os.stat(NEW_DB).st_size == 0:
            os.remove(NEW_DB)

    def openDatabase(self):
        self.dbCon = QSqlDatabase.addDatabase("QSQLITE")
        self.dbCon.setDatabaseName(NEW_DB)

        if not self.dbCon.open():
            QMessageBox.critical(
                None,
                "App Name - Error !"
                "Database Error: %s" % self.dbCon.lastError().databaseText(),
            )
            sys.exit(1)

    def displayTable(self):
        self.openDatabase()

        query = QSqlQuery("SELECT word_key, stem, category, WORDS.timestamp, "
                          "COUNT(word_key) "
                          "AS frequency, WORDS.definition "
                          "FROM LOOKUPS "
                          "JOIN WORDS WHERE word_key == WORDS.id "
                          "GROUP BY word_key "
                          "ORDER BY COUNT(word_key) DESC")

        category_text = {"0": "Learning", "1": "Mastered"}

        while query.next():
            rows = self.view.rowCount()
            self. view.setRowCount(rows + 1)
            self.view.setItem(
                rows, 0, QTableWidgetItem(self.formatWordKey(query.value(0))))
            self.view.setItem(
                rows, 1, QTableWidgetItem(query.value(1)))
            self.view.setItem(
                rows, 2, QTableWidgetItem(category_text[str(query.value(2))]))
            self.view.setItem(
                rows, 3, QTableWidgetItem(
                    str(datetime.fromtimestamp(int(query.value(3)/1000)))[:10]
                    )
                )
            self.view.setItem(
                rows, 4, QTableWidgetItem(str(query.value(4))))
            self.view.setItem(
                rows, 5, QTableWidgetItem(query.value(5).replace("\n", " ")))

        query.finish()
        self.closeDatabase()

        self.view.resizeColumnsToContents()
        header = self.view.horizontalHeader()
        for i in range(len(COLUMNS)-1):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(
            len(COLUMNS)-1, QHeaderView.ResizeMode.Stretch)

    def createDisplayTable(self, layout):
        self.view = QTableWidget()

        self.view.setColumnCount(len(COLUMNS))
        self.view.verticalHeader().setVisible(False)
        self.view.setHorizontalHeaderLabels(COLUMNS)
        self.view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.view)

    @staticmethod
    def formatWordKey(word):
        return word[word.find(":")+1:]

    @staticmethod
    def kindleConnected():
        if sys.platform == "win32":
            try:
                drives = win32api.GetLogicalDriveStrings()
                # iterates through each drive letter
                for i in range(len(drives)//4):
                    # checks if drive letter is called 'Kindle'
                    currentDrive = drives[i*4:(i+1)*4]
                    if (win32api.GetVolumeInformation(currentDrive)[0] ==
                            "Kindle" and
                            win32file.GetDriveType(currentDrive) ==
                            win32file.DRIVE_REMOVABLE):
                        return True, currentDrive[0]
                return False, ""
            except win32api.error:
                print("Error! Can't Access Windows Drive Information")
                return False, ""
        return False, ""

    def showButtons(self, layout):
        db_location_button = QPushButton("Select DB Location")
        db_location_button.clicked.connect(self.selectDbLocationClicked)
        layout.addWidget(db_location_button)

        anki_location_button = QPushButton("Select Anki Location")
        anki_location_button.clicked.connect(self.ankiLocationClicked)
        layout.addWidget(anki_location_button)

        sync_with_kindle_button = QPushButton("Sync with Kindle")
        sync_with_kindle_button.clicked.connect(self.syncKindleClicked)
        layout.addWidget(sync_with_kindle_button)

        export_button = QPushButton("Export")
        export_button.clicked.connect(self.exportClicked)
        layout.addWidget(export_button)

    def getKindleDBPath(self):
        return os.path.join(
            f"{self.kindleConnected()[1][0]}:",
            "system",
            "vocabulary",
            "vocab.db"
            )

    def getNumberRows(self):
        if not os.path.isfile(NEW_DB):
            return 0

        self.openDatabase()

        count_query = QSqlQuery("SELECT COUNT(word) FROM WORDS")
        count_query.next()
        currentWords = count_query.value(0)
        self.closeDatabase()

        return currentWords

    def exportDatabase(self, location):
        self.openDatabase()

        query = QSqlQuery("""
                        SELECT WORDS.id, word, stem, COUNT(word_key)
                          AS frequency, WORDS.definition, usage
                        FROM LOOKUPS
                        JOIN WORDS WHERE word_key = WORDS.id
                        GROUP BY word_key
                        ORDER BY COUNT(word_key) DESC
                    """)

        f = open(location, "w", encoding="utf-8")
        wordID, word, stem, frequency, definition = (i for i in range(5))
        while query.next():
            f.write(
                f"{query.value(word)} ({query.value(stem)})"
                f"\t{self.getAllWordUsages(query, wordID, word)}"
                f"\t{self.formatDefinitions(query.value(definition))}"
                f"\t{query.value(frequency)}"
                "\t1"
                "\n"
            )
        f.close()

        self.closeDatabase()

    @staticmethod
    def formatUsage(usage, word):
        return usage.replace(word, f"<b><u>{word}</u></b>")

    @staticmethod
    def formatDefinitions(definition):
        return definition.replace("\n", " <br>")

    def getAllWordUsages(self, query, wordID, wordIndex):
        usagesQuery = QSqlQuery()
        usagesQuery.prepare("SELECT usage FROM LOOKUPS WHERE "
                            "word_key=:currentWord")
        usagesQuery.bindValue(":currentWord", query.value(wordID))
        usagesQuery.exec()

        usages = ""
        index = 1
        while usagesQuery.next():
            formattedString = self.formatUsage(
                usagesQuery.value(0), query.value(wordIndex))
            usages += f"{index}) {formattedString} <br>"
            index += 1

        return usages

    def closeDatabase(self):
        self.dbCon.close()
        del self.dbCon
        QSqlDatabase.removeDatabase(QSqlDatabase.database().connectionName())

    @staticmethod
    def createNewColumns():
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN definition TEXT;"):
            print("definition column already exists")
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN example TEXT;"):
            print("example column already exists")
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN synonyms TEXT;"):
            print("synonyms column already exists")
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN antonyms TEXT;"):
            print("antonyms column already exists")
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN pronunciation TEXT;"):
            print("pronunciation column already exists")
        if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN image TEXT;"):
            print("image column already exists")

    @staticmethod
    def scrapeWordDefinition(word):
        response = requests.get(
            "https://api.dictionaryapi.dev/api/v2/entries/en/" +
            word
            )
        try:
            response_text = json.loads(response.text)
        except Exception as cloudflareError:
            print(type(cloudflareError))
            print("cloudflare")
            return "cloudflare"

        if type(response_text) is list:
            print("The requested word could not be found in the dictionary")
            return ""

        listOfDefinitions = ""
        for word in response_text[0]["meanings"]:
            listOfDefinitions += word["partOfSpeech"] + "\n"
            for i, definition in enumerate(word["definitions"]):
                listOfDefinitions += (
                    str(i+1) + ". " +
                    definition['definition'] + "\n"
                )
            listOfDefinitions += "\n"

        # remove the newline character from the end of the string
        return listOfDefinitions[:-1]


app = QApplication(sys.argv)
w = Ui_KindleRevenant()
w.show()
app.shutdown()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Ui_KindleRevenant()
    widget.show()
    sys.exit(app.exec())
