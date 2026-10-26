# BaanDee Branch Stock Readiness

## Project Overview
ต้นแบบเว็บไซต์สำหรับตรวจสอบความพร้อมของสินค้าแยกตามสาขา
ผู้ใช้สามารถค้นหาและกรองสินค้า ดูจำนวนคงเหลือ ตรวจสอบรายละเอียด
บันทึกหมายเหตุ และดาวน์โหลดข้อมูลเป็น CSV

## Data Sources
- BaanDee-provided dataset: ข้อมูลสินค้า
- Synthetic branch inventory: ข้อมูลสต็อกจำลองสำหรับสาธิต
- สต็อกจำลองไม่ใช่สต็อกจริงจาก BaanDee

## Stock Status Rules
- จำนวนคงเหลือ = 0: หมดสต็อก
- จำนวนคงเหลือ > 0 และ <= จุดสั่งเติม: ใกล้หมด
- จำนวนคงเหลือ > จุดสั่งเติม: พร้อมจำหน่าย

กฎเหล่านี้เป็นกฎของต้นแบบ ไม่ใช่นโยบายที่ยืนยันจาก BaanDee

## Features
- เลือกสาขาและค้นหาสินค้า
- กรองตามสถานะสินค้า
- ดูจำนวนคงเหลือ จุดสั่งเติม และเวลาข้อมูล
- บันทึกและเรียกดูหมายเหตุ
- ดาวน์โหลดผลการค้นหาเป็น CSV

## Data Quality
แยกข้อมูลดิบ ข้อมูลสะอาด และข้อมูลที่ต้องตรวจสอบ
รายงานคุณภาพข้อมูลและผลทดสอบอยู่ใน data/reports/

## Project Structure
- src/app.py: Streamlit application
- data/raw/: original input data
- data/generated/: synthetic demo data
- data/cleaned/: cleaned and integrated data
- data/quarantine/: records requiring review
- data/reports/: quality and test reports
- tests/: automated tests, if present

## Run
Install:
pip install streamlit pandas

Run from the project root:
streamlit run src/app.py

## Test Results
See data/reports/test_results.csv.
T01-T05 are automated checks.
T06-T08 are manual checks reported by the project owner.

## Limitations
- Branch stock is synthetic demonstration data.
- The prototype is not connected to a live BaanDee inventory API.
- Notes are stored in a local CSV file, not a production database.
- The timestamp represents the timestamp in the dataset.
