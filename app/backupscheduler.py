from model import User, Sheet
from oauth2client import client
from googlesheets import GoogleSheet
from splitwise import Splitwise
import datetime
import utils
import logging
import httplib2
import calendar
from logging.handlers import RotatingFileHandler
from logger import Logger

### Add Logging ###
#log = logging.getLogger("BACKUPLOGGER")
#log.addHandler(Logger.getBackupHandler())

def getGoogleCredentials(app, user):

    tokenExpiry = utils.stringToDatetime(user.googleTokenExpiry)

    googlecredentials = client.GoogleCredentials(
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        access_token=user.googleAccessToken,
        refresh_token=user.googleRefreshToken,
        token_expiry=tokenExpiry,
        token_uri=user.googleTokenURI,
        revoke_uri=user.googleRevokeURI,
        user_agent=None
    )

    if googlecredentials.access_token_expired:
        app.logger.debug("Google credentials for %s expired. Asking for new token",user.email)
        http = httplib2.Http()
        googlecredentials.refresh(http)
        user.googleAccessToken = googlecredentials.access_token
        user.googleTokenExpiry = utils.datetimeToString(googlecredentials.token_expiry)
        user.save()

    return googlecredentials


def getSpreadSheetIdFromName(user,googleSheet,spreadsheetName):

    spreadsheet = Sheet.query.filter_by(user_id=user.id,sheetName=spreadsheetName).first()

    if spreadsheet is not None:
        return googleSheet.getSpreadSheet(spreadsheet.sheetId)

    return None


def createSheetForUser(user,googleSheet,spreadsheetName,currMonth):
    spreadsheet = googleSheet.createSpreadSheet(spreadsheetName,currMonth)

    usersheet = Sheet()
    usersheet.user_id = user.id
    usersheet.sheetName = spreadsheetName
    usersheet.sheetId = spreadsheet.getId()
    usersheet.save()

    return spreadsheet

def createSheetInSpreadSheet(googleSheet,spreadsheet,currMonth):
    googleSheet.addSheet(spreadsheet.getId(),currMonth)

def backupData(app):
    with app.app_context():

        #Current time
        now = datetime.datetime.now()

        app.logger.debug("Backing up data")

        users = User.query.filter_by(splitwiseAccess=True,googleSheetAccess=True).all()

        for user in users:

            app.logger.debug("Backing up data for %s",user.email)

            #Get google credentials of user
            googlecredentials = getGoogleCredentials(app,user)

            #Get googlesheet object
            googleSheet = GoogleSheet(googlecredentials)

            #Make splitwise object
            splitwiseObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])

            #Authenticate splitwise object
            splitwiseObj.setAccessToken({"oauth_token":user.splitwiseToken,"oauth_token_secret":user.splitwiseTokenSecret})

            ########### Get data from Splitwise ####################
            app.logger.debug("Getting data for user from splitwise")

            friends = splitwiseObj.getFriends()

            ########## Put data in Google #########################
            spreadsheetName = "SplitwiseBackup"+str(now.year)
            currMonth  = calendar.month_name[now.month]


            #Check if spreadsheet is there if not create a spreadsheet
            spreadsheet = getSpreadSheetIdFromName(user,googleSheet,spreadsheetName)

            #Sheet is not there, make a new sheet
            if spreadsheet is None:
                app.logger.debug("Sheet does not exist. Creating a new sheet")
                spreadsheet = createSheetForUser(user, googleSheet, spreadsheetName, currMonth)

            #Check if sheet is present in the spreadsheet
            sheets = spreadsheet.getSheets()

            sheetPresent = False

            for sheet in sheets:
                if sheet.getName() == currMonth:
                    sheetPresent = True
                    break

            #If not create a current month sheet
            if not sheetPresent:
                createSheetInSpreadSheet(googleSheet,spreadsheet,currMonth)

            #Data to be updated in sheet
            updateData = {
            }

            #Get current sheet data
            data =  googleSheet.getData(spreadsheet.getId(),currMonth+"!A1:Z1000")

            if data is None:
                data = [["Date"]]
                updateData["A1"] = "Date"

            nameRow = data[0]
            newRow = len(data)+1
            lastFilledCol = len(nameRow)

            updateData["A"+str(newRow)]=str(now)

            for friend in friends:
                name = friend.getFirstName()
                amount = ""

                for balance in friend.getBalances():
                    amount += balance.getCurrencyCode()+" "+balance.getAmount()+"\n"

                try:#Name is in the list
                    index = nameRow.index(name)
                except ValueError as ve: #Name is not in the list
                    index = lastFilledCol
                    lastFilledCol += 1
                    updateData[utils.getColumnNameFromIndex(index)+"1"] = name

                updateData[utils.getColumnNameFromIndex(index)+str(newRow)] = amount

            googleSheet.batchUpdate(spreadsheet.getId(),updateData)

            app.logger.debug("Data backed up successfully for %s ",user.email)
