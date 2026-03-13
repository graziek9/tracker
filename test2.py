import json
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://gamma-api.polymarket.com"


def fetch_events_for_tag(session, tag_id, limit=50):
    params = {
        "tag_id": tag_id,
        "active": "true",
        "closed": "false",
        "limit": limit,
    }

    resp = session.get(f"{BASE}/events", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def stream_sports_events_fast(max_workers=8, limit_per_tag=50):

    session = requests.Session()

    sports_resp = session.get(f"{BASE}/sports", timeout=10)
    sports_resp.raise_for_status()
    sports = sports_resp.json()

    tag_jobs = []

    for sport in sports:
        sport_name = sport.get("sport", "Unknown")
        tags_raw = sport.get("tags", "")
        tag_ids = [t.strip() for t in str(tags_raw).split(",") if t.strip()]

        for tag_id in tag_ids:
            tag_jobs.append((sport_name, tag_id))

    seen_events = set()
    rows = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_map = {
            executor.submit(fetch_events_for_tag, session, tag_id, limit_per_tag): (sport_name, tag_id)
            for sport_name, tag_id in tag_jobs
        }

        for future in as_completed(future_map):

            sport_name, tag_id = future_map[future]

            try:
                events = future.result()
            except Exception as e:
                print(f'error "{sport_name}" "{tag_id}" "{e}"', flush=True)
                continue

            for ev in events:

                event_id = ev.get("id")

                if event_id in seen_events:
                    continue
                seen_events.add(event_id)

                title = ev.get("title", "")
                markets = ev.get("markets", []) or []

                if not markets:

                    row = {
                        "sport": sport_name,
                        "title": title,
                        "event_id": event_id,
                        "market_id": None,
                        "yes_token_id": None,
                        "no_token_id": None,
                        "token_ids": None,
                        "liquidity": None,
                        "volume": None,
                        "end_date": ev.get("endDate"),
                    }

                    rows.append(row)

                    print(row, flush=True)
                    continue

                for market in markets:

                    market_id = market.get("id")
                    liquidity = market.get("liquidity")
                    volume = market.get("volume")
                    end_date = market.get("endDate", ev.get("endDate"))

                    tokens = market.get("tokens", []) or []
                    outcomes = market.get("outcomes")
                    clob_token_ids = market.get("clobTokenIds")

                    yes_token_id = None
                    no_token_id = None
                    token_ids = None

                    if isinstance(tokens, list) and tokens:
                        token_ids = []

                        for token in tokens:

                            tid = (
                                token.get("token_id")
                                or token.get("id")
                                or token.get("asset_id")
                                or token.get("tokenId")
                            )

                            outcome_name = str(
                                token.get("outcome")
                                or token.get("name")
                                or ""
                            ).strip().lower()

                            if tid is not None:
                                token_ids.append(tid)

                            if outcome_name == "yes":
                                yes_token_id = tid
                            elif outcome_name == "no":
                                no_token_id = tid

                    if (yes_token_id is None or no_token_id is None) and clob_token_ids and outcomes:
                        try:
                            parsed_token_ids = json.loads(clob_token_ids) if isinstance(clob_token_ids, str) else clob_token_ids
                            parsed_outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes

                            if isinstance(parsed_token_ids, list):
                                token_ids = parsed_token_ids

                            if isinstance(parsed_token_ids, list) and isinstance(parsed_outcomes, list):
                                for outcome_name, tid in zip(parsed_outcomes, parsed_token_ids):

                                    outcome_name = str(outcome_name).strip().lower()

                                    if outcome_name == "yes":
                                        yes_token_id = tid
                                    elif outcome_name == "no":
                                        no_token_id = tid
                        except Exception:
                            pass

                    row = {
                        "sport": sport_name,
                        "title": title,
                        "event_id": event_id,
                        "market_id": market_id,
                        "yes_token_id": yes_token_id,
                        "no_token_id": no_token_id,
                        "token_ids": token_ids,
                        "liquidity": liquidity,
                        "volume": volume,
                        "end_date": end_date,
                    }

                    rows.append(row)

                    print(row, flush=True)

    df = pd.DataFrame(rows)

    return df


def expand_tokens(df):
    """
    Takes the markets dataframe and returns a dataframe
    with one row per token (YES and NO).
    """

    rows = []

    for _, r in df.iterrows():

        base = {
            "sport": r["sport"],
            "title": r["title"],
            "event_id": r["event_id"],
            "market_id": r["market_id"],
            "liquidity": r["liquidity"],
            "volume": r["volume"],
            "end_date": r["end_date"],
        }

        # YES token
        if pd.notna(r["yes_token_id"]):
            rows.append({
                **base,
                "token_id": r["yes_token_id"],
                "outcome": "YES"
            })

        # NO token
        if pd.notna(r["no_token_id"]):
            rows.append({
                **base,
                "token_id": r["no_token_id"],
                "outcome": "NO"
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":

    # STEP 1 (data download)
    df = stream_sports_events_fast(max_workers=8, limit_per_tag=25)
    print("\nFinished scraping.")
    print(df.head())
    print(f"\nTotal rows: {len(df)}")
    df.to_csv("sports_markets.csv", index=False)
    print("\nCSV file saved as: sports_markets.csv")

    # STEP 2 (dataframe expansion)
    tokens_df = expand_tokens(df)
    tokens_df.to_csv("sports_tokens.csv", index=False)
    print("\nToken-level dataframe:")
    print(tokens_df.head())
    print(f"\nTotal tokens: {len(tokens_df)}")
