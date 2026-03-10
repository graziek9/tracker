import pandas as pd
from collections import defaultdict

EPSILON = 1e-9


def normalize_side(side: str) -> str:
    side = str(side).strip().upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError(f"Unexpected side: {side}")
    return side


def load_trades(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Parse timestamp like: 10/03/2026 03:00:27
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    # Basic cleaning
    df["side"] = df["side"].map(normalize_side)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["size"] = pd.to_numeric(df["size"], errors="coerce")

    required_cols = [
        "user",
        "user_address",
        "timestamp",
        "title",
        "side",
        "outcome",
        "price",
        "size",
        "slug",
        "eventSlug",
        "proxyWallet",
        "asset",
        "conditionId",
        "transactionHash",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=["timestamp", "price", "size", "user_address", "conditionId", "outcome"])
    df = df.sort_values(["user_address", "conditionId", "outcome", "timestamp", "transactionHash"]).reset_index(drop=True)
    return df


def reconstruct_positions(df: pd.DataFrame):
    """
    Reconstruct positions per:
        user_address + conditionId + outcome

    Assumptions:
    - BUY increases position
    - SELL decreases position
    - size is number of shares
    - weighted average cost is tracked for positive inventory
    - if inventory goes negative, we allow it but cost basis for shorts is not modeled here
    """

    state = defaultdict(lambda: {
        "shares": 0.0,
        "avg_price": 0.0,
        "cost_basis": 0.0,       # only for positive shares
        "realized_pnl": 0.0,
        "last_trade_time": None,
        "title": None,
        "slug": None,
        "eventSlug": None,
        "user": None,
        "proxyWallet": None,
        "asset": None,
    })

    history_rows = []

    for _, row in df.iterrows():
        key = (row["user_address"], row["conditionId"], row["outcome"])
        pos = state[key]

        side = row["side"]
        price = float(row["price"])
        size = float(row["size"])

        old_shares = pos["shares"]
        old_avg_price = pos["avg_price"]

        # Store metadata
        pos["title"] = row["title"]
        pos["slug"] = row["slug"]
        pos["eventSlug"] = row["eventSlug"]
        pos["user"] = row["user"]
        pos["proxyWallet"] = row["proxyWallet"]
        pos["asset"] = row["asset"]
        pos["last_trade_time"] = row["timestamp"]

        if side == "BUY":
            # Case 1: already long or flat
            if pos["shares"] >= -EPSILON:
                new_shares = pos["shares"] + size
                new_cost_basis = pos["cost_basis"] + size * price

                pos["shares"] = new_shares
                pos["cost_basis"] = new_cost_basis
                pos["avg_price"] = (new_cost_basis / new_shares) if abs(new_shares) > EPSILON else 0.0

            # Case 2: currently short (negative shares), buy reduces short first
            else:
                # This logic only updates shares, not full short-PnL accounting
                pos["shares"] += size

                # If buy crosses from short to long, reset long basis for leftover
                if pos["shares"] > EPSILON:
                    leftover_long = pos["shares"]
                    pos["cost_basis"] = leftover_long * price
                    pos["avg_price"] = price
                elif abs(pos["shares"]) <= EPSILON:
                    pos["shares"] = 0.0
                    pos["cost_basis"] = 0.0
                    pos["avg_price"] = 0.0

        elif side == "SELL":
            # Case 1: selling from a long inventory
            if pos["shares"] > EPSILON:
                closing_size = min(size, pos["shares"])
                pos["realized_pnl"] += closing_size * (price - pos["avg_price"])

                pos["shares"] -= size

                # If still long, reduce cost basis proportionally
                if pos["shares"] > EPSILON:
                    pos["cost_basis"] = pos["shares"] * pos["avg_price"]
                elif abs(pos["shares"]) <= EPSILON:
                    pos["shares"] = 0.0
                    pos["cost_basis"] = 0.0
                    pos["avg_price"] = 0.0
                else:
                    # Went net short; long inventory fully closed
                    pos["cost_basis"] = 0.0
                    pos["avg_price"] = 0.0

            # Case 2: already flat or short
            else:
                pos["shares"] -= size
                # We do not model short cost basis here
                pos["cost_basis"] = 0.0
                pos["avg_price"] = 0.0

        history_rows.append({
            "user": row["user"],
            "user_address": row["user_address"],
            "conditionId": row["conditionId"],
            "outcome": row["outcome"],
            "timestamp": row["timestamp"],
            "transactionHash": row["transactionHash"],
            "title": row["title"],
            "side": side,
            "trade_price": price,
            "trade_size": size,
            "shares_before": old_shares,
            "shares_after": pos["shares"],
            "avg_price_before": old_avg_price,
            "avg_price_after": pos["avg_price"],
            "realized_pnl_cumulative": pos["realized_pnl"],
            "is_closed_after_trade": abs(pos["shares"]) <= EPSILON,
        })

    positions_rows = []
    for (user_address, condition_id, outcome), pos in state.items():
        shares = 0.0 if abs(pos["shares"]) <= EPSILON else pos["shares"]

        positions_rows.append({
            "user": pos["user"],
            "user_address": user_address,
            "conditionId": condition_id,
            "outcome": outcome,
            "title": pos["title"],
            "slug": pos["slug"],
            "eventSlug": pos["eventSlug"],
            "proxyWallet": pos["proxyWallet"],
            "asset": pos["asset"],
            "shares": shares,
            "avg_price": pos["avg_price"],
            "cost_basis": pos["cost_basis"],
            "realized_pnl": pos["realized_pnl"],
            "last_trade_time": pos["last_trade_time"],
            "position_status": (
                "closed" if abs(shares) <= EPSILON
                else "long_open" if shares > 0
                else "short_or_unknown_open"
            ),
        })

    history_df = pd.DataFrame(history_rows)
    positions_df = pd.DataFrame(positions_rows)

    return history_df, positions_df


if __name__ == "__main__":
    # Replace with your file path
    csv_path = "trade_log_user_P1.csv"

    trades = load_trades(csv_path)
    trade_history, positions = reconstruct_positions(trades)

    # Save outputs
    trade_history.to_csv("reconstructed_trade_history_user_P1.csv", index=False)
    positions.to_csv("reconstructed_positions_user_P1.csv", index=False)

    # Optional: only open positions
    open_positions = positions[positions["position_status"] != "closed"].copy()
    open_positions.to_csv("open_positions.csv", index=False)

    print("Done.")
    print(f"Trades processed: {len(trades)}")
    print(f"Positions reconstructed: {len(positions)}")
    print(f"Open positions: {len(open_positions)}")