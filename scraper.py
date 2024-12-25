from flask import Flask, request, jsonify
import requests
from azure.cosmos import CosmosClient, PartitionKey
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration for Cosmos DB
COSMOS_ENDPOINT = "https://yourfash.documents.azure.com:443"
COSMOS_KEY = "XZnbXrc0l9cHuaWAsGuWuvSbbvj7nsZT6GABomWjT6qp5aVEJdkb7Am7nxBEtlNHBdi4X36QDKnAACDbZrWCHw=="
KEEPA_API_KEY = "2u04omevbnatrcf8oofg5atl8bbflaci23ja9s3fjhmh78i0jjeaukcgr7lca8hj"
DATABASE_NAME = "AmazonProducts"
CONTAINER_NAME = "Products"

cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/id")
)

class KeepaCategoryFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.keepa.com/query"

    def fetch_products_by_category(
        self,
        category_id: int,
        product_limit: int,
        domain: int = 10,
        min_reviews: int = 5
    ):
        print(f"Fetching products for category ID {category_id}...")
        fetched_asins = set()
        page = 1

        while len(fetched_asins) < product_limit:
            params = {"key": self.api_key, "domain": domain}
            json_data = {
                "category": category_id,
                "sort": "sales",
                "minReviewCount": min_reviews,
                "perPage": 1000,
                "page": page,
            }

            retries = 0
            while retries < 6:
                try:
                    response = requests.get(self.base_url, params=params, json=json_data)
                    if response.status_code == 429:
                        backoff = 2 ** retries
                        print(f"Rate limit reached. Retrying in {backoff} seconds...")
                        time.sleep(backoff)
                        retries += 1
                        continue

                    response.raise_for_status()
                    data = response.json()
                    products = data.get("asinList", [])
                    fetched_asins.update(products)

                    if len(products) == 0:
                        return list(fetched_asins)

                    page += 1
                    break
                except requests.exceptions.RequestException as e:
                    retries += 1
                    time.sleep(2 ** retries)
                    print(f"Error fetching products: {e}")

        return list(fetched_asins)

def fetch_and_save_product_details(asins, max_products=8000):
    batch_size = 100
    products_saved = 0

    def fetch_and_save_batch(batch_asins):
        nonlocal products_saved
        params = {"key": KEEPA_API_KEY, "domain": 10, "asin": ",".join(batch_asins), "stats": 30}
        retries = 0

        while retries < 6:
            try:
                response = requests.get("https://api.keepa.com/product", params=params)
                if response.status_code == 429:
                    time.sleep(2 ** retries)
                    retries += 1
                    continue

                response.raise_for_status()
                products = response.json().get("products", [])
                for product in products:
                    if products_saved >= max_products:
                        return
                    try:
                        cleaned_data = clean_product_data(product)
                        container.upsert_item(cleaned_data)
                        products_saved += 1
                    except Exception as e:
                        print(f"Error saving product {product.get('asin')}: {e}")
                return
            except Exception as e:
                retries += 1
                time.sleep(2 ** retries)
                print(f"Error fetching batch {batch_asins}: {e}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_and_save_batch, asins[i:i + batch_size])
            for i in range(0, len(asins), batch_size)
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error in thread execution: {e}")

def clean_product_data(product):
    stats = product.get("stats", {})
    current_price = stats.get("current") if stats else None
    product['csv']= None
    product['salesRanks']= None
    product['stats'] = None
    return {
        "id": product.get("asin"),
        "title": product.get("title", "Unknown Title"),
        "brand": product.get("brand", "Unknown Brand"),
        "price": current_price,
        "last_updated": product.get("lastUpdate", None),
        "category": product.get("categoryTree", []),
        "raw": product,
    }