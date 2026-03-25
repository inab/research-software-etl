from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
import random

PUBLICATIONS_COLLECTION = "publicationsMetadataDev"
TOOLS_COLLECTION = "toolsDev"


def main():

    publications_col = mongo_adapter.get_collection(PUBLICATIONS_COLLECTION)
    tools_col = mongo_adapter.get_collection(TOOLS_COLLECTION)

     # 1) Publications with no title and no doi
    bad_publications_query = {
        "$and": [
            {
                "$or": [
                    {"data.title": {"$exists": False}},
                    {"data.title": None},
                    {"data.title": ""},
                ]
            },
            {
                "$or": [
                    {"data.doi": {"$exists": False}},
                    {"data.doi": None},
                    {"data.doi": ""},
                ]
            },
        ]
    }

    bad_publications = list(publications_col.find(bad_publications_query))
    bad_publications_by_id_str = {str(doc["_id"]): doc for doc in bad_publications}
    bad_publication_id_strs = list(bad_publications_by_id_str.keys())

    print(f"Found {len(bad_publication_id_strs)} bad publication docs")

    # 2) Tools linked to bad publications
    bad_tools_query = {
        "data.publication": {"$in": bad_publication_id_strs}
    }

    bad_matching_tools = list(
        tools_col.find(
            bad_tools_query,
            {
                "_id": 1,
                "data.name": 1,
                "data.publication": 1,
                "data.url": 1,
            },
        )
    )

    print(f"Found {len(bad_matching_tools)} tools linked to bad publications")

    for tool in bad_matching_tools:
        tool_data = tool.get("data", {})
        pub_ids = tool_data.get("publication", [])

        matched_bad_pubs = [
            bad_publications_by_id_str[pub_id]
            for pub_id in pub_ids
            if pub_id in bad_publications_by_id_str
        ]

        print("\n" + "=" * 100)
        print(f"TOOL ID: {tool['_id']}")
        print(f"TOOL NAME: {tool_data.get('name')}")
        print(f"TOOL URL: {tool_data.get('url')}")
        print(f"NUMBER OF BAD PUBLICATIONS LINKED: {len(matched_bad_pubs)}")

        for pub in matched_bad_pubs:
            print("  -" * 20)
            print(f"  PUB ID: {pub['_id']}")
            print(f"  TITLE: {pub.get('data', {}).get('title')}")
            print(f"  DOI: {pub.get('data', {}).get('doi')}")

    # 3) Sample 5 complete publications as sanity check
    complete_publications_query = {
        "$or": [
            {"data.title": {"$exists": True, "$nin": [None, ""]}},
            {"data.doi": {"$exists": True, "$nin": [None, ""]}},
        ]
    }

    complete_publications = list(
        publications_col.find(
            complete_publications_query,
            {
                "_id": 1,
                "data.title": 1,
                "data.doi": 1,
            },
        )
    )

    print(f"\nFound {len(complete_publications)} complete publication docs")

    if not complete_publications:
        print("No complete publications found. Cannot run sanity check.")
        return

    sample_size = min(5, len(complete_publications))
    sampled_publications = random.sample(complete_publications, sample_size)

    print(f"\nChecking {sample_size} random complete publications for linked tools...\n")

    for pub in sampled_publications:
        pub_id_str = str(pub["_id"])
        pub_data = pub.get("data", {})

        tools_for_pub = list(
            tools_col.find(
                {"data.publication": pub_id_str},
                {
                    "_id": 1,
                    "data.name": 1,
                    "data.url": 1,
                    "data.publication": 1,
                },
            )
        )

        print("=" * 100)
        print(f"PUBLICATION ID: {pub['_id']}")
        print(f"TITLE: {pub_data.get('title')}")
        print(f"DOI: {pub_data.get('doi')}")
        print(f"LINKED TOOLS FOUND: {len(tools_for_pub)}")

        for tool in tools_for_pub:
            print(f"  TOOL ID: {tool['_id']}")
            print(f"  TOOL NAME: {tool.get('data', {}).get('name')}")
            print(f"  TOOL URL: {tool.get('data', {}).get('url')}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
    