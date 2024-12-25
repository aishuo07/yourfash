from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from scraper import KeepaCategoryFetcher, fetch_and_save_product_details  # Importing from scraper.py

app = Flask(__name__)
CORS(app)  # Enable CORS
logger = logging.getLogger()
logger.setLevel(logging.INFO)
KEEPA_API_KEY = "2u04omevbnatrcf8oofg5atl8bbflaci23ja9s3fjhmh78i0jjeaukcgr7lca8hj"


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

@app.route("/fetch-products", methods=["POST"])
def fetch_products():
    try:
        data = request.json
        category_id = data.get("category_id")
        product_limit = data.get("limit", 8000)

        if not category_id:
            return jsonify({"error": "category_id is required"}), 400

        if product_limit > 8000:
            product_limit = 8000

        fetcher = KeepaCategoryFetcher(KEEPA_API_KEY)
        asins = fetcher.fetch_products_by_category(category_id, product_limit)

        if not asins:
            return jsonify({"message": "No products found for the given category"}), 200

        fetch_and_save_product_details(asins, max_products=product_limit)

        return jsonify({"message": f"Successfully fetched and saved up to {product_limit} products"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy'
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
