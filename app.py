import hmac
import json
import os
import re

import anthropic
import numpy as np
import pandas as pd
import streamlit as st
from rank_bm25 import BM25Okapi

from prompt import SYSTEM

K = 5                     # sections given to Claude (chosen in the analysis)
MAX_LIVE_QUESTIONS = 5    # per visit, to cap spending

STOPWORDS = {"how", "much", "many", "what", "when", "can", "do", "i", "am", "is", "are", "the",
             "a", "an", "to", "of", "my", "me", "if", "in", "for", "on", "be", "have", "with",
             "after", "or", "does", "should", "by", "from", "it", "get", "that", "this", "and"}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "covered": {"type": "boolean"},
        "answer": {"type": "string"},
        "cited_sections": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["covered", "answer", "cited_sections"],
    "additionalProperties": False,
}


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS]


@st.cache_data
def load_data():
    sections = pd.read_csv("data/sections.csv", dtype={"section": str})
    saved = pd.read_csv("data/answers_k5.csv", dtype=str, keep_default_na=False)
    return sections, saved


@st.cache_resource
def load_search(_sections):
    return BM25Okapi([tokenize(t) for t in _sections["text"]])


sections, saved = load_data()
bm25 = load_search(sections)


def search(question, k=K):
    scores = bm25.get_scores(tokenize(question))
    return sections["section"].iloc[np.argsort(-scores)[:k]].tolist()


def build_context(section_ids):
    chosen = sections.set_index("section").loc[section_ids]
    return "\n\n".join(f"[s. {sid}] {row['title']}\n{row['text']}" for sid, row in chosen.iterrows())


def ask_claude(client, question):
    retrieved = search(question)
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium",
                       "format": {"type": "json_schema", "schema": ANSWER_SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user",
                   "content": f"Sections of the Canada Labour Code, Part III:\n\n{build_context(retrieved)}"
                              f"\n\nQuestion: {question}"}],
    )
    if response.stop_reason == "refusal":
        return {"covered": False, "answer": "This question couldn't be answered.", "cited_sections": []}
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def show_answer(covered, answer, cited):
    if not covered:
        st.info("Not covered by the sections found.")
    st.markdown(answer)
    for sid in cited:
        match = sections[sections["section"] == sid]
        if len(match):
            with st.expander(f"s. {sid}: {match.iloc[0]['title']}"):
                st.write(match.iloc[0]["text"])


def secret(name):
    try:
        return st.secrets[name]
    except Exception:          # no secrets file locally, or the name isn't set
        return None


# --- 1. The answer first ---
st.title("Canada Labour Code: plain-language answers")
st.caption("Get plain-language answers to questions about federal labour standards, with the exact section of the Canada Labour Code cited for each answer. In testing, Claude cited the right section for 83% of test questions and flagged both off-topic test questions as not covered.")
st.warning("Federal labour standards only (Canada Labour Code, Part III), which apply to federally "
           "regulated workplaces such as banks, airlines and telecoms. Information, not legal advice. "
           "Not an official version of the law.")
with st.sidebar:
    st.header("How it works")
    st.markdown("""
            **How it works**
            1. Keyword search (BM25) finds the most relevant sections of the law.
            2. The top 5 sections are given to Claude.
            3. Claude answers in plain language and cites the sections it used.

            **How well (tested on 20 questions: 18 answerable, 2 off-topic)**
            - The right section was cited for 83% of answerable questions.
            - Both off-topic questions were marked as not covered, and the user was told.
            - Every miss came from search not finding the right section. When Claude had it, it always cited it.

            **Limits**
            - Everyday words like "laid off" or "fired" can miss, because the law says "terminates" and "dismissed".
            - Small test set (20 questions), so treat the numbers as a guide.
            - Law current to December 29, 2025 (last amended December 12, 2025).
        """)

browse, live = st.tabs(["Tested questions", "Ask your own"])

# --- 2. Browse the 20 tested questions (saved answers, no API calls) ---
with browse:
    st.markdown("These are the 20 questions used to evaluate the system, with Claude's saved answers.")
    question = st.selectbox("Pick a question", saved["question"])
    row = saved[saved["question"] == question].iloc[0]
    cited = [c for c in row["cited_sections"].split(";") if c]
    show_answer(row["covered"] == "True", row["answer"], cited)

# --- 3. Live questions, behind a password ---
with live:
    password = secret("APP_PASSWORD")
    api_key = secret("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")   # locally: your env variable
    if not (password and api_key):
        st.info("Live questions are switched off on this deployment. Browse the tested questions instead.")
    else:
        entered = st.text_input("Access code", type="password")
        if entered and not hmac.compare_digest(entered, password):
            st.error("That access code isn't right.")
        elif entered:
            asked = st.session_state.get("asked", 0)
            user_q = st.text_input("Your question about federal labour standards")
            clicked = st.button("Ask", disabled=asked >= MAX_LIVE_QUESTIONS)
            if clicked and user_q and asked < MAX_LIVE_QUESTIONS:   # the check, not just the button, enforces the cap
                st.session_state["asked"] = asked + 1
                try:
                    with st.spinner("Finding the relevant sections…"):
                        result = ask_claude(anthropic.Anthropic(api_key=api_key), user_q)
                    show_answer(result["covered"], result["answer"], result["cited_sections"])
                except anthropic.APIError:
                    st.error("The answer service isn't available right now. Please try again later.")
            # drawn after the click is handled, so the count is always current
            st.caption(f"Questions left this visit: {MAX_LIVE_QUESTIONS - st.session_state.get('asked', 0)}")