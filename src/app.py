
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data/cleaned/branch_product_readiness.csv"
OVERRIDE_FILE = BASE / "data/cleaned/manual_stock_notes.csv"

st.set_page_config(
    page_title="BaanDee Stock Readiness",
    layout="wide"
)

st.title("BaanDee | Branch Stock Readiness")
st.caption(
    "ต้นแบบเพื่อการศึกษา — ข้อมูลสต็อกสาขาเป็นข้อมูลจำลอง ไม่ใช่ยอดจริง"
)

# --------------------------------------------------
# API DEMO
# --------------------------------------------------
st.subheader("ตรวจสอบการเชื่อมต่อ API จำลอง")

api_url = os.getenv(
    "BAANDEE_API_URL",
    "http://127.0.0.1:8000"
).strip().rstrip("/")

api_order_id = st.text_input(
    "รหัสคำสั่งซื้อสำหรับทดสอบ API",
    value="ORD-260728-1842",
    key="api_order_id"
)

if st.button("ตรวจสอบ API", key="check_api"):
    if not api_url:
        st.error("ยังไม่ได้กำหนด URL ของ API")
    elif not api_order_id.strip():
        st.warning("กรุณากรอกรหัสคำสั่งซื้อ")
    else:
        try:
            response = requests.get(
                f"{api_url}/orders/{quote(api_order_id.strip(), safe='')}",
                timeout=5
            )

            if response.status_code == 200:
                st.success("เชื่อมต่อ API สำเร็จ และพบคำสั่งซื้อ")
                try:
                    st.json(response.json())
                except ValueError:
                    st.error("API ส่งข้อมูลกลับมาในรูปแบบที่ไม่ถูกต้อง")

            elif response.status_code == 404:
                st.warning(
                    "เชื่อมต่อ API ได้ แต่ไม่พบคำสั่งซื้อรหัสนี้"
                )
                st.write(response.text)

            else:
                st.error(
                    f"API ตอบกลับด้วย HTTP {response.status_code}"
                )

        except requests.exceptions.Timeout:
            st.error("API ตอบสนองช้าเกิน 5 วินาที (Timeout)")

        except requests.exceptions.ConnectionError:
            st.error(
                "เชื่อมต่อ API ไม่สำเร็จ "
                "โปรดตรวจสอบ URL และสถานะของบริการ"
            )

        except requests.exceptions.RequestException as exc:
            st.error(f"เกิดข้อผิดพลาดในการเรียก API: {exc}")

st.caption(
    "หมายเหตุ: API นี้เป็นระบบจำลอง ต้องเปิดบริการ API "
    "และตั้งค่า BAANDEE_API_URL ให้ตรงกับที่อยู่จริงก่อนใช้งาน"
)

st.divider()

# --------------------------------------------------
# LOAD INVENTORY DATA
# --------------------------------------------------
if not DATA_FILE.exists():
    st.error(
        "ไม่พบไฟล์ข้อมูล branch_product_readiness.csv "
        "กรุณาตรวจสอบไฟล์ข้อมูลใน repository"
    )
    st.stop()

try:
    df = pd.read_csv(DATA_FILE)
except Exception as exc:
    st.error(f"อ่านไฟล์ข้อมูลไม่สำเร็จ: {exc}")
    st.stop()

required_columns = [
    "branch_id",
    "product_id",
    "product_name",
    "category",
    "available_qty",
    "reorder_level",
    "readiness_status",
    "as_of",
    "inventory_source",
    "product_source",
    "unit_price_thb",
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    st.error(f"ไฟล์ข้อมูลขาดคอลัมน์: {', '.join(missing_columns)}")
    st.stop()

# --------------------------------------------------
# LOAD REVIEW NOTES
# --------------------------------------------------
note_columns = [
    "branch_id",
    "product_id",
    "note",
    "created_at",
]

if OVERRIDE_FILE.exists():
    try:
        notes = pd.read_csv(OVERRIDE_FILE)
    except Exception:
        notes = pd.DataFrame(columns=note_columns)
else:
    notes = pd.DataFrame(columns=note_columns)

for col in note_columns:
    if col not in notes.columns:
        notes[col] = ""

st.info(
    "กฎสถานะ: 0 = หมดสต็อก, "
    "มากกว่า 0 แต่ไม่เกินจุดสั่งเติม = ใกล้หมด, "
    "มากกว่าจุดสั่งเติม = พร้อมจำหน่าย"
)

# --------------------------------------------------
# BRANCH SELECTION
# --------------------------------------------------
branches = sorted(
    df["branch_id"].dropna().astype(str).unique().tolist()
)

if not branches:
    st.warning("ไม่มีข้อมูลสาขาให้เลือก")
    st.stop()

branch = st.selectbox("เลือกสาขา", branches)
branch_df = df[df["branch_id"].astype(str) == branch].copy()

c1, c2, c3 = st.columns(3)

c1.metric("จำนวนรายการสินค้าในสาขา", len(branch_df))
c2.metric(
    "หมดสต็อก",
    int((branch_df["readiness_status"] == "หมดสต็อก").sum())
)
c3.metric(
    "ใกล้หมด",
    int((branch_df["readiness_status"] == "ใกล้หมด").sum())
)

# --------------------------------------------------
# SEARCH AND FILTER
# --------------------------------------------------
st.subheader("ค้นหาสินค้า")

search = st.text_input("ค้นหาด้วยรหัสสินค้า หรือชื่อสินค้า")

status_options = [
    "ทั้งหมด",
    "พร้อมจำหน่าย",
    "ใกล้หมด",
    "หมดสต็อก",
]

status = st.selectbox("กรองตามสถานะ", status_options)

filtered = branch_df.copy()

if search.strip():
    q = search.strip().lower()

    filtered = filtered[
        filtered["product_id"].astype(str).str.lower().str.contains(
            q, na=False, regex=False
        )
        | filtered["product_name"].astype(str).str.lower().str.contains(
            q, na=False, regex=False
        )
    ]

if status != "ทั้งหมด":
    filtered = filtered[filtered["readiness_status"] == status]

display_cols = [
    "branch_id",
    "product_id",
    "product_name",
    "category",
    "available_qty",
    "reorder_level",
    "readiness_status",
    "as_of",
    "inventory_source",
    "product_source",
]

st.dataframe(
    filtered[display_cols],
    use_container_width=True,
    hide_index=True
)

st.write(f"พบรายการสินค้า {len(filtered)} รายการ")

st.download_button(
    "ดาวน์โหลดผลการค้นหา CSV",
    data=filtered[display_cols].to_csv(
        index=False
    ).encode("utf-8-sig"),
    file_name=f"stock_readiness_{branch}.csv",
    mime="text/csv",
)

# --------------------------------------------------
# PRODUCT DETAILS AND REVIEW NOTES
# --------------------------------------------------
st.subheader("รายละเอียดสินค้า")

if len(branch_df) > 0:
    product_ids = sorted(
        branch_df["product_id"].dropna().astype(str).unique().tolist()
    )

    selected_id = st.selectbox("เลือกรหัสสินค้า", product_ids)

    selected_rows = branch_df[
        branch_df["product_id"].astype(str) == selected_id
    ]

    if not selected_rows.empty:
        selected = selected_rows.iloc[0]

        left, right = st.columns(2)

        with left:
            st.write("**ชื่อสินค้า:**", selected["product_name"])
            st.write("**หมวดหมู่:**", selected["category"])
            st.write("**ราคาต่อหน่วย (บาท):**", selected["unit_price_thb"])

        with right:
            st.write("**สาขา:**", selected["branch_id"])
            st.write("**จำนวนคงเหลือ (ข้อมูลจำลอง):**", selected["available_qty"])
            st.write("**จุดสั่งเติม (กฎต้นแบบ):**", selected["reorder_level"])
            st.write("**สถานะ:**", selected["readiness_status"])
            st.write("**อัปเดตข้อมูล ณ:**", selected["as_of"])

        st.caption(
            "หลักฐาน: รหัสสินค้าและชื่อมาจากชุดข้อมูลสินค้า; "
            "จำนวนสต็อกและจุดสั่งเติมมาจากข้อมูลจำลอง; "
            "สถานะคำนวณตามกฎที่แสดงด้านบน"
        )

        st.subheader("บันทึกหมายเหตุสำหรับผู้ตรวจสอบ")

        note_text = st.text_area(
            "หมายเหตุ (บันทึกแยก ไม่แก้ยอดสต็อกต้นฉบับ)",
            key="review_note"
        )

        if st.button("บันทึกหมายเหตุ", key="save_note"):
            if not note_text.strip():
                st.warning("กรุณากรอกหมายเหตุก่อนบันทึก")
            else:
                new_note = pd.DataFrame([{
                    "branch_id": branch,
                    "product_id": selected_id,
                    "note": note_text.strip(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }])

                updated = pd.concat(
                    [notes, new_note],
                    ignore_index=True
                )

                try:
                    OVERRIDE_FILE.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )
                    updated.to_csv(OVERRIDE_FILE, index=False)
                    st.success("บันทึกหมายเหตุแล้ว")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "บันทึกหมายเหตุไม่สำเร็จ: "
                        f"{exc}"
                    )

        st.subheader("ประวัติหมายเหตุ")

        matching_notes = notes[
            (notes["branch_id"].astype(str) == branch)
            & (notes["product_id"].astype(str) == selected_id)
        ]

        if not matching_notes.empty:
            st.dataframe(
                matching_notes,
                use_container_width=True,
                hide_index=True
            )

            note_indices = matching_notes.index.tolist()

            selected_note_idx = st.selectbox(
                "เลือกหมายเหตุเดิมที่ต้องการแก้ไข",
                options=note_indices,
                format_func=lambda idx: (
                    f"{notes.loc[idx, 'created_at']} — "
                    f"{str(notes.loc[idx, 'note'])[:80]}"
                ),
                key="edit_note_choice"
            )

            edited_text = st.text_area(
                "แก้ไขข้อความหมายเหตุ",
                value=str(notes.loc[selected_note_idx, "note"]),
                key="edit_note_text"
            )

            if st.button("บันทึกการแก้ไข", key="update_note"):
                if not edited_text.strip():
                    st.warning("หมายเหตุห้ามเป็นข้อความว่าง")
                else:
                    notes.loc[
                        selected_note_idx, "note"
                    ] = edited_text.strip()

                    if "updated_at" not in notes.columns:
                        notes["updated_at"] = ""

                    notes.loc[
                        selected_note_idx, "updated_at"
                    ] = datetime.now(timezone.utc).isoformat()

                    try:
                        notes.to_csv(OVERRIDE_FILE, index=False)
                        st.success("แก้ไขหมายเหตุเดิมแล้ว")
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            "แก้ไขหมายเหตุไม่สำเร็จ: "
                            f"{exc}"
                        )
        else:
            st.write("ยังไม่มีหมายเหตุสำหรับสินค้านี้")
else:
    st.info("สาขานี้ไม่มีรายการสินค้า")
