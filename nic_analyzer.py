from __future__ import annotations
from typing import Dict, Any

from llm_client import USER_PROMPT_TEMPLATE, call_typhoon


class FinancialHealthAnalyzer:
    """
    NIC Financial Health Analyzer
    -----------------------------
    รับ input รายเดือนของผู้ใช้ แล้วคืนค่าผลวิเคราะห์เป็น dictionary
    ใช้กับ Dashboard ได้ตรง ๆ
    """

    def analyze_nic_data(
        self,
        net_income_monthly: float,
        needs_food: float,
        needs_housing: float,
        needs_transport: float,
        needs_utilities: float,
        needs_insurance: float,
        needs_debt: float,
        wants_misc: float,
    ) -> Dict[str, Any]:
        # ---- Safety check ----
        if net_income_monthly <= 0:
            raise ValueError("net_income_monthly ต้องมากกว่า 0")

        # -------------------------
        # 1. Basic Calculations
        # -------------------------
        total_needs = (
            needs_food
            + needs_housing
            + needs_transport
            + needs_utilities
            + needs_insurance
            + needs_debt
        )

        total_expenses_monthly = total_needs + wants_misc
        savings_monthly_derived = net_income_monthly - total_expenses_monthly

        # 50/30/20 actual %
        actual_needs_pct = (total_needs / net_income_monthly) * 100
        actual_wants_pct = (wants_misc / net_income_monthly) * 100
        actual_savings_pct = (savings_monthly_derived / net_income_monthly) * 100

        # DSR %
        dsr_pct = (needs_debt / net_income_monthly) * 100

        # -------------------------
        # 2. Survival Ratio & DSR status
        # -------------------------
        # Survival ratio (รายได้ / รายจ่าย)
        if total_expenses_monthly > 0:
            survival_ratio = net_income_monthly / total_expenses_monthly
        else:
            # ถ้าไม่มีรายจ่ายเลย ให้ถือว่าปลอดภัยสุด ๆ
            survival_ratio = float("inf")

        # DSR status
        if dsr_pct <= 15:
            dsr_status = "Excellent"
        elif dsr_pct <= 40:
            dsr_status = "Good"
        elif dsr_pct <= 50:
            dsr_status = "Warning"
        else:
            dsr_status = "Critical"

        # Survival Status (Basic Liquidity)
        if survival_ratio < 1.0:
            survival_status = "Critical"
        elif survival_ratio < 3.0:  # 1.0 ถึง 2.9
            survival_status = "Warning"
        else:  # 3.0 ขึ้นไป
            survival_status = "Excellent"

        # -------------------------
        # 3. Health Score (0–100)
        # -------------------------

        # 1) Needs Control (20 pts)
        # ลงโทษเฉพาะถ้า Needs > 50% (ค่อย ๆ หักคะแนนจนถึง 0 ที่ 75%)
        needs_penalty_ratio = (actual_needs_pct - 50) / 25
        needs_score_raw = 20 * (1 - needs_penalty_ratio)
        needs_score = max(0.0, min(20.0, needs_score_raw))

        # 2) Wants Control (20 pts)
        # ลงโทษเมื่อ Wants > 30% (ค่อย ๆ หักคะแนนจนถึง 0 ที่ 50%)
        wants_penalty_ratio = (actual_wants_pct - 30) / 20
        wants_score_raw = 20 * (1 - wants_penalty_ratio)
        wants_score = max(0.0, min(20.0, wants_score_raw))

        # 3) Savings Power (35 pts)
        # ให้เต็มถ้าออม ≥ 20% (สัดส่วนตรง)
        savings_score_raw = 35 * (actual_savings_pct / 20)
        savings_score = max(0.0, min(35.0, savings_score_raw))

        # 4) Debt Control (25 pts)
        # ให้เต็มเมื่อ DSR = 0 และหักคะแนนเรื่อย ๆ จนถึง 0 ที่ DSR = 40
        debt_score_raw = 25 * (1 - dsr_pct / 40)
        debt_score = max(0.0, min(25.0, debt_score_raw))

        health_score = needs_score + wants_score + savings_score + debt_score

        # -------------------------
        # 4. Overspent Check & Culprit
        # -------------------------
        # เกิน 50% สำหรับ Needs, เกิน 30% สำหรับ Wants
        needs_surplus_amount = max(0.0, total_needs - 0.50 * net_income_monthly)
        wants_surplus_amount = max(0.0, wants_misc - 0.30 * net_income_monthly)

        # Culprit = รายการ Needs ที่หนักสุด
        needs_items = {
            "food": needs_food,
            "housing": needs_housing,
            "transport": needs_transport,
            "utilities": needs_utilities,
            "insurance": needs_insurance,
            "debt": needs_debt,
        }

        culprit_item = None
        culprit_amount = 0.0
        if total_needs > 0:
            culprit_item = max(needs_items, key=needs_items.get)
            culprit_amount = needs_items[culprit_item]

        # -------------------------
        # 5. Insight Text Generation
        # -------------------------
        insights = []

        # 1) Survival ratio crisis
        if survival_ratio <= 1.0:
            insights.append(
                "⏰ สถานะการเงินของคุณเริ่มน่าห่วง "
                "เพราะรายจ่ายรวมต่อเดือนสูงกว่าหรือเกือบเท่ารายได้สุทธิ "
                "ควรพิจารณาลดรายจ่ายเร่งด่วน"
            )

        # 2) DSR warning / critical
        if dsr_status in ("Warning", "Critical"):
            insights.append(
                f"⚠️ ภาระหนี้ของคุณอยู่ในระดับ '{dsr_status}' "
                f"(DSR ≈ {dsr_pct:.1f}%) ควรระวังการสร้างหนี้เพิ่มและวางแผนปิดหนี้เดิม"
            )

        # 3) Needs / Wants overspent
        if needs_surplus_amount > 0:
            msg = (
                f"🍛 ค่าใช้จ่ายจำเป็น (Needs) เกินกรอบ 50% ของรายได้ ประมาณ {needs_surplus_amount:,.0f} บาท/เดือน"
            )
            if culprit_item is not None:
                msg += f" โดยหมวดที่ใช้เยอะสุดคือ '{culprit_item}' ประมาณ {culprit_amount:,.0f} บาท/เดือน"
            insights.append(msg)

        if wants_surplus_amount > 0:
            insights.append(
                f"🎮 ค่าใช้จ่ายไม่จำเป็น (Wants) เกินกรอบ 30% ของรายได้ "
                f"ประมาณ {wants_surplus_amount:,.0f} บาท/เดือน ลองตัดรายจ่ายฟุ่มเฟือยบางส่วน"
            )

        # 4) ถ้าไม่พบปัญหาใหญ่
        if not insights:
            insights.append(
                "✅ ภาพรวมการใช้เงินของคุณอยู่ในเกณฑ์ดี ทั้งสัดส่วน Needs/Wants/การออม "
                "และภาระหนี้ยังไม่เกินจุดเสี่ยง"
            )

        weakness_insight_text = " ".join(insights)

        # -------------------------
        # 6. Return as dict (for Dashboard)
        # -------------------------
        return {
            "health_score": round(health_score, 2),
            "actual_needs_pct": round(actual_needs_pct, 2),
            "actual_wants_pct": round(actual_wants_pct, 2),
            "actual_savings_pct": round(actual_savings_pct, 2),
            "dsr_pct": round(dsr_pct, 2),
            "dsr_status": dsr_status,
            "survival_ratio": round(survival_ratio, 2)
            if survival_ratio != float("inf")
            else float("inf"),
            "survival_status": survival_status,
            "weakness_insight_text": weakness_insight_text,
            "culprit_item": culprit_item,
            "culprit_amount": round(culprit_amount, 2),
            "needs_surplus_amount": round(needs_surplus_amount, 2),
            "wants_surplus_amount": round(wants_surplus_amount, 2),
        }


def generate_dashboard_data(params: Dict[str, float]) -> Dict[str, Any]:
    """
    ฟังก์ชันหลักที่ให้ FS เรียกทีเดียวจบ

    params: dict ที่ key ตรงกับ analyze_nic_data:
        - net_income_monthly
        - needs_food
        - needs_housing
        - needs_transport
        - needs_utilities
        - needs_insurance
        - needs_debt
        - wants_misc

    return: dict ที่มีทั้งตัวเลข (numbers) + ข้อความ 3 panel (panels)
    """
    analyzer = FinancialHealthAnalyzer()

    # 1) คำนวณตัวเลขทั้งหมด
    numbers = analyzer.analyze_nic_data(**params)

    # 2) สร้าง prompt เพื่อถาม Typhoon
    user_prompt = USER_PROMPT_TEMPLATE.format(**numbers)

    # 3) ยิง Typhoon ได้ left/middle/right panel กลับมา
    panels = call_typhoon(user_prompt)

    # 4) รวมเป็นก้อนเดียว ส่งกลับให้ backend / frontend
    return {
        "numbers": numbers,
        "panels": panels,
    }
