#!/usr/bin/env python3
import argparse
import os
import pymongo
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-size", type=int, default=5000)
    args = ap.parse_args()


    from dotenv import load_dotenv
    load_dotenv()

    mongo_host = os.getenv('MONGO_HOST', 'localhost')
    mongo_port = int(os.getenv('MONGO_PORT', '27018'))
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PWD')
    mongo_auth_src = os.getenv('MONGO_AUTH_SRC', 'admin')

    client = pymongo.MongoClient(
        'mongodb://127.0.0.1:27018',
        username=mongo_user,
        password=mongo_pass,
        authSource=mongo_auth_src,
        authMechanism='SCRAM-SHA-256',
        maxPoolSize=100,
        serverSelectionTimeoutMS=5000
                )

    client.admin.command('ping')
    col = client['oeb-research-software']['pretoolsDev']


    prefixes = ["bioconda/", "opeb_metrics/"]
    regex = f"^({'|'.join(prefixes)})"

    pipeline = [
        {"$addFields": {"_id_str": {"$toString": "$_id"}}},
        {"$match": {"_id_str": {"$regex": regex}}},
        {"$project": {"_id": 1}},
    ]

    batch, total = [], 0
    for doc in col.aggregate(pipeline, allowDiskUse=True):
        batch.append(doc["_id"])
        if len(batch) >= args.batch_size:
            total += len(batch)
            if not args.dry_run:
                col.delete_many({"_id": {"$in": batch}})
            batch.clear()

    if batch:
        total += len(batch)
        if not args.dry_run:
            col.delete_many({"_id": {"$in": batch}})

    if args.dry_run:
        print(f"[DRY RUN] Would delete {total} documents where _id starts with {prefixes}")
    else:
        print(f"Deleted {total} documents where _id starts with {prefixes}")

if __name__ == "__main__":
    main()