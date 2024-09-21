from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up Google Sheets API credentials
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
logger.info('Authorized with Google Sheets API')

spreadsheet_name = 'your_fash_waitlist'
sheet = client.open(spreadsheet_name).sheet1

@app.route('/add_to_sheet', methods=['POST', 'OPTIONS'])
def add_to_sheet():
    logger.info('Starting add_to_sheet')
    
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://ocissor.github.io',
                'Access-Control-Allow-Methods': 'OPTIONS, POST',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            },
            'body': ''
        }

    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': 'https://ocissor.github.io',
        'Access-Control-Allow-Headers': 'Content-Type, Postman-Token, sec-ch-ua, sec-ch-ua-platform, sec-ch-ua-mobile, Referer, User-Agent',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }

    try:
        # Extract data from the request
        body = request.json
        name = body.get('name')
        mobile = body.get('mobile')
        email = body.get('email')
        reason = body.get('reason')

        logger.info(f'Data extracted: {name}, {mobile}, {email}, {reason}')

        # Add data to Google Sheets
        logger.info('Appending data to the sheet')
        sheet.append_row([name, mobile, email, reason])
        logger.info('Data added to Google Sheets successfully')

        return jsonify({
            'statusCode': 200,
            'headers': headers,
            'message': 'Data added to Google Sheets successfully!'
        }), 200

    except gspread.SpreadsheetNotFound:
        logger.error('Spreadsheet not found. Ensure the name is correct and the document is shared with the service account.')
        return jsonify({
            'statusCode': 404,
            'headers': headers,
            'error': 'Spreadsheet not found'
        }), 404

    except Exception as e:
        logger.error(f'Error: {str(e)}', exc_info=True)
        return jsonify({
            'statusCode': 500,
            'headers': headers,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
