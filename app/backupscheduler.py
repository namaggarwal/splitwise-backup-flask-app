from model import User, Sheet
from oauth2client import client
from googlesheets import GoogleSheet
from splitwise import Splitwise
import datetime
import utils
import logging
import httplib2
import calendar

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
            try:
                googlecredentials = getGoogleCredentials(app,user)
            except:
                app.logger.error("Error getting Google credentials of user "+user.email)
                continue

            #Get googlesheet object
            try:
                googleSheet = GoogleSheet(googlecredentials)
            except:
                app.logger.error("Error getting sheet from Google of user "+user.email)
                continue

            #Make splitwise object
            splitwiseObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])

            #Authenticate splitwise object
            splitwiseObj.setAccessToken({"oauth_token":user.splitwiseToken,"oauth_token_secret":user.splitwiseTokenSecret})

            ########### Get data from Splitwise ####################
            app.logger.debug("Getting data for user from splitwise")

            try:
                friends = splitwiseObj.getFriends()
            except:
                app.logger.error("Error getting data from Splitwise for user "+user.email)
                continue

            ########## Put data in Google #########################
            spreadsheetName = "SplitwiseBackup"+str(now.year)
            currMonth  = calendar.month_name[now.month]


            #Check if spreadsheet is there if not create a spreadsheet
            spreadsheet = getSpreadSheetIdFromName(user,googleSheet,spreadsheetName)

            #Sheet is not there, make a new sheet
            if spreadsheet is None:
                app.logger.debug("Sheet does not exist. Creating a new sheet")
                try:
                    spreadsheet = createSheetForUser(user, googleSheet, spreadsheetName, currMonth)
                except:
                    app.logger.error("Error creating sheet for user "+user.email)
                    continue

            #Check if sheet is present in the spreadsheet
            sheets = spreadsheet.getSheets()

            sheetPresent = False

            for sheet in sheets:
                if sheet.getName() == currMonth:
                    sheetPresent = True
                    break

            #If not create a current month sheet
            if not sheetPresent:
                app.logger.debug("Sheet for month %s does not exist. Creating new sheet",currMonth)
                try:
                    createSheetInSpreadSheet(googleSheet,spreadsheet,currMonth)
                    app.logger.debug("Sheet for month %s created",currMonth)
                except:
                    app.logger.error("Error creating sheet for month %s for user %s",currMonth,user.email)
                    continue


            #Data to be updated in sheet
            updateData = {
            }

            #Get current sheet data
            try:
                app.logger.debug("Getting current sheet data for user %s",user.email)
                data =  googleSheet.getData(spreadsheet.getId(),currMonth+"!A1:Z1000")
            except:
                app.logger.error("Error sheet data for month %s for user %s",currMonth,user.email)
                continue


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

            try:
                app.logger.debug("Saving data for user %s",user.email)
                googleSheet.batchUpdate(spreadsheet.getId(),updateData)
            except:
                app.logger.error("Error saving sheet data for month %s for user %s",currMonth,user.email)
                continue


            user.lastBackupTime = now
            user.save()

            app.logger.debug("Data backed up successfully for %s ",user.email)
