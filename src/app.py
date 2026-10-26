
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/content/BaanDee_Project/BaanDee_Class1_Student")
DATA_FILE = BASE / "data/cleaned/branch_product_readiness.csv"
OVERRIDE_FILE = BASE / "data/cleaned/manual_stock_notes.csv"

st.set_page_config(page_title="BaanDee Stock Readiness", layout="wide")
st.title("BaanDee | Branch Stock Readiness")
st.caption("ต้นแบบเพื่อการศึกษา — ข้อมูลสต็อกสาขาเป็นข้อมูลจำลอง ไม่ใช่ยอดจริง")

if not DATA_FILE.exists():
    st.error("ไม่พบไฟล์ข้อมูล กรุณารันขั้นตอนเตรียมและเชื่อมข้อมูลก่อน")
    st.stop()

df = pd.read_csv(DATA_FILE)

# เก็บบันทึกหมายเหตุแยกจากข้อมูลต้นฉบับ
if OVERRIDE_FILE.exists():
    notes = pd.read_csv(OVERRIDE_FILE)
else:
    notes = pd.DataFrame(columns=[
        "branch_id", "product_id", "note", "created_at"
    ])

st.info("กฎสถานะ: 0 = หมดสต็อก, มากกว่า 0 แต่ไม่เกินจุดสั่งเติม = ใกล้หมด, มากกว่าจุดสั่งเติม = พร้อมจำหน่าย")

branches = sorted(df["branch_id"].dropna().unique().tolist())
branch = st.selectbox("เลือกสาขา", branches)

branch_df = df[df["branch_id"] == branch].copy()

c1, c2, c3 = st.columns(3)
c1.metric("จำนวนสินค้าในสาขา", len(branch_df))
c2.metric("หมดสต็อก", int((branch_df["readiness_status"] == "หมดสต็อก").sum()))
c3.metric("ใกล้หมด", int((branch_df["readiness_status"] == "ใกล้หมด").sum()))

st.subheader("ค้นหาสินค้า")
search = st.text_input("ค้นหาด้วยรหัสสินค้า หรือชื่อสินค้า")
status_options = ["ทั้งหมด", "พร้อมจำหน่าย", "ใกล้หมด", "หมดสต็อก"]
status = st.selectbox("กรองตามสถานะ", status_options)

filtered = branch_df.copy()
if search.strip():
    q = search.strip().lower()
    filtered = filtered[
        filtered["product_id"].astype(str).str.lower().str.contains(q, na=False)
        | filtered["product_name"].astype(str).str.lower().str.contains(q, na=False)
    ]
if status != "ทั้งหมด":
    filtered = filtered[filtered["readiness_status"] == status]

display_cols = [
    "branch_id", "product_id", "product_name", "category",
    "available_qty", "reorder_level", "readiness_status",
    "as_of", "inventory_source", "product_source"
]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

st.download_button(
    "ดาวน์โหลดผลการค้นหา CSV",
    data=filtered[display_cols].to_csv(index=False).encode("utf-8-sig"),
    file_name=f"stock_readiness_{branch}.csv",
    mime="text/csv"
)

st.subheader("รายละเอียดสินค้า")
if len(branch_df):
    product_ids = sorted(branch_df["product_id"].unique().tolist())
    selected_id = st.selectbox("เลือกรหัสสินค้า", product_ids)
    selected = branch_df[branch_df["product_id"] == selected_id].iloc[0]

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
        "หลักฐาน: รหัสสินค้าและชื่อมาจากชุดข้อมูล BaanDee; "
        "จำนวนสต็อกและจุดสั่งเติมมาจากข้อมูลจำลอง; "
        "สถานะคำนวณตามกฎที่แสดงด้านบน"
    )

    st.subheader("บันทึกหมายเหตุสำหรับผู้ตรวจสอบ")
    note_text = st.text_area(
        "หมายเหตุ (บันทึกแยก ไม่แก้ยอดสต็อกต้นฉบับ)",
        key="review_note"
    )
    if st.button("บันทึกหมายเหตุ"):
        new_note = pd.DataFrame([{
            "branch_id": branch,
            "product_id": selected_id,
            "note": note_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }])
        updated = pd.concat([notes, new_note], ignore_index=True)
        updated.to_csv(OVERRIDE_FILE, index=False)
        st.success("บันทึกหมายเหตุแล้ว โดยเก็บแยกจากข้อมูลสต็อกต้นฉบับ")
        st.rerun()

    st.subheader("ประวัติหมายเหตุ")
    if len(notes):
        st.dataframe(
            notes[
                (notes["branch_id"] == branch)
                & (notes["product_id"] == selected_id)
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("ยังไม่มีหมายเหตุสำหรับสินค้า")
