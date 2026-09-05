"""Evidence-grounded recovery operations assistant."""

import re

import streamlit as st


def _find_transaction(frame, prompt):
    prompt_lower = prompt.lower()
    matches = frame[
        frame["Payment ID"].str.lower().apply(lambda value: value in prompt_lower)
        | frame["_id"].str.lower().apply(lambda value: value in prompt_lower)
    ]
    return matches.iloc[0].to_dict() if not matches.empty else None


def answer(prompt, data, frame):
    prompt_lower = prompt.lower().strip()
    txn = _find_transaction(frame, prompt_lower)
    if txn is not None:
        return {
            "summary": f"Payment {txn['Payment ID']} was classified as {txn['AI diagnosis'].lower()} after a {txn['Failure reason'].lower()} failure.",
            "detail": f"The recorded recommendation is {txn['Action'].lower()}. The current policy state is {txn['Policy status'].lower()}, with outcome {txn['Outcome'].lower()}.",
            "evidence": [("Payment", txn["Payment ID"]), ("Failure reason", txn["Failure reason"]), ("Category", txn["AI diagnosis"]), ("Policy", txn["Policy status"])],
        }
    if any(word in prompt_lower for word in ("at risk", "risk", "exposure")):
        metrics = data["metrics"]
        return {"summary": f"The current batch has {metrics['total_transactions']} payments and {metrics['total_at_risk']:,.2f} rupees at risk.", "detail": "This value comes directly from the recovery_metrics view currently loaded from Supabase.", "evidence": [("Payments analyzed", metrics["total_transactions"]), ("Revenue at risk", f"Rs {metrics['total_at_risk']:,.2f}"), ("Recovered", f"Rs {metrics['total_recovered']:,.2f}")]}
    if "recovered" in prompt_lower:
        metrics = data["metrics"]
        return {"summary": f"The current recovered amount is Rs {metrics['total_recovered']:,.2f} across {metrics['recovered_count']} payments.", "detail": f"The count-based recovery rate is {metrics['recovery_rate_pct']:.1f}%.", "evidence": [("Recovered value", f"Rs {metrics['total_recovered']:,.2f}"), ("Recovered payments", metrics["recovered_count"]), ("Recovery rate", f"{metrics['recovery_rate_pct']:.1f}%")]}
    if "most revenue" in prompt_lower or "failure reason" in prompt_lower:
        grouped = frame.groupby("Failure reason")["Amount"].sum().sort_values(ascending=False)
        reason, amount = grouped.index[0], grouped.iloc[0]
        return {"summary": f"{reason} currently represents the largest recorded exposure at Rs {amount:,.2f}.", "detail": "This is a descriptive aggregation of the loaded transaction records, not a new model prediction.", "evidence": [("Failure reason", reason), ("Recorded exposure", f"Rs {amount:,.2f}"), ("Source", "transactions table")]}
    if "why did" in prompt_lower and "fail" in prompt_lower:
        grouped = frame.groupby("Failure reason").agg(Count=("_id", "count"), Exposure=("Amount", "sum")).sort_values("Exposure", ascending=False)
        reason = grouped.index[0]
        return {"summary": f"The most common recorded failure pattern by exposure is {reason.lower()}.", "detail": "Ask with an 8-character payment ID for a payment-specific diagnosis and policy explanation.", "evidence": [("Top recorded reason", reason), ("Payments with reason", int(grouped.iloc[0]["Count"])), ("Exposure", f"Rs {grouped.iloc[0]['Exposure']:,.2f}")]}
    if "safest" in prompt_lower or "retry" in prompt_lower:
        retryable = frame[frame["AI diagnosis"].str.lower() == "retryable"]
        return {"summary": f"There are {len(retryable)} retryable records in the current batch.", "detail": "The rules engine recommends silent retry only for retryable failures on their first attempt. Fraud-risk records are excluded from automated retry.", "evidence": [("Eligible category", "retryable"), ("Candidate records", len(retryable)), ("Guardrail", "first attempt only")]}
    if "escalat" in prompt_lower or "not retried" in prompt_lower:
        fraud = frame[frame["AI diagnosis"].str.lower() == "fraud risk"]
        return {"summary": f"Fraud-risk records are escalated or left for manual review; {len(fraud)} such records are present.", "detail": "Automatic contact is blocked by the deterministic safety rule for fraud risk.", "evidence": [("Category", "fraud_risk"), ("Policy", "automatic contact blocked"), ("Manual review records", len(fraud))]}
    return {"summary": "I can answer from the current recovery records.", "detail": "Try a payment ID, or ask about risk, recovered revenue, failure reasons, retry candidates, or escalations.", "evidence": [("Data source", "Supabase recovery records"), ("Mode", "Evidence-grounded")]}


def render(data, frame):
    st.markdown('<div class="ui-kicker">RECOVERAI COPILOT</div><div class="ui-title">AI Recovery Assistant</div><div class="ui-subtitle">Evidence-grounded recovery intelligence for payment operations.</div>', unsafe_allow_html=True)
    prompts = ["Why did this payment fail?", "Which failure reason causes the most revenue loss?", "Which payments are safest to retry?", "Why was this payment escalated?", "How much revenue is currently at risk?", "How much revenue has been recovered?"]
    st.markdown('<div class="ui-card"><div style="font-weight:700;margin-bottom:10px">Suggested prompts</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for index, prompt in enumerate(prompts):
        with cols[index % 3]:
            if st.button(prompt, key=f"prompt_{index}"):
                st.session_state["assistant_prompt"] = prompt
                st.session_state["assistant_answer"] = answer(prompt, data, frame)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    with st.form("assistant_form", clear_on_submit=False):
        prompt = st.text_input("Ask about revenue, payments or recovery decisions", value=st.session_state.get("assistant_prompt", ""), placeholder="Ask about revenue, payments or recovery decisions...", label_visibility="collapsed")
        submitted = st.form_submit_button("Send", type="secondary")
    if submitted and prompt.strip():
        st.session_state["assistant_prompt"] = prompt
        st.session_state["assistant_answer"] = answer(prompt, data, frame)
    response = st.session_state.get("assistant_answer")
    if response:
        st.markdown('<div class="ui-card ui-card--elevated"><div style="font-weight:700;margin-bottom:10px">RecoverAI Copilot</div>', unsafe_allow_html=True)
        st.write(response["summary"])
        st.write(response["detail"])
        st.markdown("**Evidence from current records**")
        st.dataframe(response["evidence"], hide_index=True, width="stretch")
        st.caption("Responses are concise summaries of transaction, intervention, audit, and metrics data. No hidden reasoning is exposed.")
        st.markdown('</div>', unsafe_allow_html=True)
