from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CHECKPOINTS = ROOT / "data" / "checkpoints"
GROUND_TRUTH = ROOT / "data" / "ground_truth"


def normalize_customer_id(value: object) -> str | None:
    if pd.isna(value):
        return None
    compact = re.sub(r"[^A-Z0-9]", "", str(value).strip().upper())
    match = re.fullmatch(r"CUS(\d{5})", compact)
    return f"CUS-{match.group(1)}" if match else None


def normalize_order_reference(value: object, crosswalk: pd.DataFrame) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip().upper()
    canonical = re.fullmatch(r"ORD-\d{6}-\d{4}", raw)
    if canonical:
        return raw
    matches = crosswalk.loc[crosswalk["raw_reference"].str.upper() == raw, "canonical_order_id"]
    return matches.iloc[0] if len(matches) == 1 else None


def unsafe_digits_only_match(reference: str, orders: pd.DataFrame) -> list[str]:
    """Intentionally unsafe version used only for the contained teaching failure."""
    digits = re.sub(r"\D", "", reference)
    suffix = digits[-4:]
    return orders.loc[orders["order_id"].str.endswith(suffix), "order_id"].tolist()


def parse_mixed_date(value: object) -> tuple[str | None, str]:
    if pd.isna(value) or not str(value).strip():
        return None, "missing"
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).isoformat(), "parsed"
        except ValueError:
            pass
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        a, b, _ = [int(x) for x in text.split("/")]
        if a <= 12 and b <= 12:
            return None, "ambiguous"
        try:
            return datetime.strptime(text, "%d/%m/%Y").date().isoformat(), "parsed"
        except ValueError:
            return None, "invalid"
    return None, "invalid"


def validate_join_quality(joined: pd.DataFrame) -> dict[str, int]:
    counts = joined.groupby("ticket_id", dropna=False)["order_id"].nunique(dropna=True)
    return {
        "tickets": int(joined["ticket_id"].nunique()),
        "matched_once": int((counts == 1).sum()),
        "unmatched": int((counts == 0).sum()),
        "multiply_matched": int((counts > 1).sum()),
    }


def build_checkpoints() -> dict[str, int]:
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    customers = pd.read_csv(RAW / "customers.csv", dtype=str)
    orders = pd.read_csv(RAW / "orders.csv", dtype=str)
    lines = pd.read_csv(RAW / "order_lines.csv", dtype=str)
    products = pd.read_csv(RAW / "products.csv", dtype=str)
    inventory = pd.read_csv(RAW / "inventory_snapshot.csv", dtype=str)
    tickets = pd.read_csv(RAW / "support_tickets.csv", dtype=str)
    crosswalk = pd.read_csv(GROUND_TRUTH / "order_reference_crosswalk.csv", dtype=str)

    naive = tickets.merge(orders, left_on="order_reference", right_on="order_id", how="left", suffixes=("_ticket", "_order"))
    naive.to_csv(CHECKPOINTS / "01_naive_join.csv", index=False)

    customers["customer_id_clean"] = customers["customer_id"].map(normalize_customer_id)
    tickets["customer_id_clean"] = tickets["customer_id"].map(normalize_customer_id)
    tickets["order_id_clean"] = tickets["order_reference"].map(lambda x: normalize_order_reference(x, crosswalk))
    orders["order_id_clean"] = orders["order_id"].str.strip().str.upper()
    orders["customer_id_clean"] = orders["customer_id"].map(normalize_customer_id)
    products["category_clean"] = products["category"].str.strip().str.lower().replace({"bed room":"bedding"})

    parsed = orders["order_date"].map(parse_mixed_date)
    orders["order_date_clean"] = parsed.map(lambda x: x[0])
    orders["order_date_quality"] = parsed.map(lambda x: x[1])
    ticket_parsed = tickets["created_at"].map(parse_mixed_date)
    tickets["created_at_clean"] = ticket_parsed.map(lambda x: x[0])
    tickets["created_at_quality"] = ticket_parsed.map(lambda x: x[1])

    corrected = tickets.merge(orders, on="order_id_clean", how="left", suffixes=("_ticket", "_order"))
    corrected.to_csv(CHECKPOINTS / "02_corrected_join.csv", index=False)
    customers.to_csv(CHECKPOINTS / "customers_clean.csv", index=False)
    orders.to_csv(CHECKPOINTS / "orders_clean.csv", index=False)
    tickets.to_csv(CHECKPOINTS / "tickets_clean.csv", index=False)
    products.to_csv(CHECKPOINTS / "products_clean.csv", index=False)
    lines.to_csv(CHECKPOINTS / "order_lines_clean.csv", index=False)
    inventory.to_csv(CHECKPOINTS / "inventory_snapshot_clean.csv", index=False)

    ambiguous = pd.concat([
        orders.loc[orders["order_date_quality"].isin(["ambiguous", "invalid"])].assign(source="orders"),
        tickets.loc[tickets["created_at_quality"].isin(["ambiguous", "invalid"])].assign(source="tickets"),
    ], ignore_index=True, sort=False)
    ambiguous.to_csv(CHECKPOINTS / "quarantine_dates.csv", index=False)

    duplicate_phone = customers[customers["phone"].duplicated(keep=False)].copy()
    duplicate_phone.to_csv(CHECKPOINTS / "quarantine_customer_candidates.csv", index=False)
    corrections = pd.DataFrame([
        {"record":"customer:cus00842", "field":"customer_id", "raw":"cus00842", "clean":"CUS-00842", "method":"known ID format"},
        {"record":"ticket:TKT-260731-042", "field":"order_reference", "raw":"OD1842", "clean":"ORD-260728-1842", "method":"approved source crosswalk"},
        {"record":"products:category", "field":"category", "raw":"kitchen", "clean":"kitchen", "method":"trim and lowercase"},
        {"record":"products:category", "field":"category", "raw":"Bed room", "clean":"bedding", "method":"explicit category map"},
    ])
    corrections.to_csv(CHECKPOINTS / "correction_log.csv", index=False)
    report = validate_join_quality(corrected)
    pd.DataFrame([report]).to_csv(CHECKPOINTS / "join_quality_report.csv", index=False)
    return report


if __name__ == "__main__":
    print(build_checkpoints())
