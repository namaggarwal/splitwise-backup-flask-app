import httplib2
from apiclient import discovery
from apiclient.errors import HttpError

class GoogleSheet(object):

    def __init__(self,credentials):
        credentials = credentials
        http = httplib2.Http()
        http = credentials.authorize(http)
        self.service = discovery.build('sheets', 'v4', http=http)

    def getSpreadSheet(self,spreadSheetId):
        request = self.service.spreadsheets().get(spreadsheetId=spreadSheetId)
        response = request.execute()
        return SpreadSheet(response)

    def createSpreadSheet(self,spreadsheetName,sheetName):
        spreadsheet_body = {
            "properties":{
                "title":spreadsheetName
            },
            "sheets":[{
                "properties":{
                    "title":sheetName,
                    "gridProperties":{
                        "columnCount":100
                    }
                }
            }]
        }
        request = self.service.spreadsheets().create(body=spreadsheet_body)
        response = request.execute()
        return SpreadSheet(response)

    def addSheet(self,spreadsheetId,sheetName):
        request_body = {
          "includeSpreadsheetInResponse": True,
          "responseIncludeGridData": False,
          "requests": [
            {
              "addSheet": {
                "properties": {
                  "title": sheetName,
                  "gridProperties":{
                    "columnCount":100
                  }
                }
              }
            }
          ]
        }

        request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheetId, body=request_body)
        response = request.execute()
        return SpreadSheet(response["updatedSpreadsheet"])

    def getData(self,spreadsheetId,range):
        request = self.service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=range, majorDimension="ROWS")
        response = request.execute()
        if 'values' in response:
            return response['values']
        else:
            return None


    def batchUpdate(self,spreadsheetId,data):

        request_body = {
            "data":[],
            "valueInputOption":"USER_ENTERED"
        }

        for key, value in data.iteritems():
            request_body["data"].append({"range":key,"values":[[value]]})

        request = self.service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheetId, body=request_body)
        response = request.execute()


class SpreadSheet(object):

    def __init__(self,data):

        if data is None:
            raise Exception("Cannot initiate")

        self.id = data["spreadsheetId"]
        self.name = data["properties"]["title"]

        self.sheets = []
        sheetsData = data["sheets"]

        for sheetData in sheetsData:
            self.sheets.append(Sheet(sheetData))

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def getSheets(self):
        return self.sheets


class Sheet(object):

    def __init__(self,data):

        if data is None:
            raise Exception("Cannot initiate")

        self.id = data["properties"]["sheetId"]
        self.name = data["properties"]["title"]


    def getId(self):
        return self.id

    def getName(self):
        return self.name
