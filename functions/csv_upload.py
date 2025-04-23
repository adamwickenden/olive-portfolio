import pandas as pd
from google.cloud import firestore

from datetime import datetime

def flip_date_format(date_str):
    # Parse the date in "DD-MM-YYYY" format
    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
    # Return the date in "YYYY-MM-DD" format
    return date_obj.strftime("%Y-%m-%d")


# Load CSV
df = pd.read_csv("/Users/adamwickenden/Documents/personal/olive-portfolio/src/assets/articles/articles.csv")

# Initialize Firestore
db = firestore.Client()

for x in db.collections():
    print(x)

# Choose a Firestore collection
collection_name = "covers"

# Upload each row as a document
for index, row in df.iterrows():
    doc_data = row.to_dict()

    doc_data["DATE"] = flip_date_format(doc_data["DATE"])

    # Optional: use a specific field as document ID
    doc_ref = db.collection(collection_name).document()  # Auto-ID
    doc_ref.set(doc_data)

print("Upload complete.")