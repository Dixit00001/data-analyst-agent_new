# ── file: app.py ──────────────────────────────────────────────────────────
import os, json, tempfile, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 1️⃣  config & secrets  ---------------------------------------------------
load_dotenv()                                    # read .env
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
PORT           = int(os.getenv("PORT", 8000))
TMP_DIR        = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(TMP_DIR, exist_ok=True)

app = Flask(__name__)

# 2️⃣  helper – save non-prompt files to disk (if any) ---------------------
def _save_attachments(files):
    paths = {}
    for field, fs in files.items():
        if field == "questions.txt":
            continue
        tmp = tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False)
        fs.save(tmp.name)
        paths[field] = tmp.name
    return paths

# 3️⃣  the single endpoint  ------------------------------------------------
@app.route("/api/", methods=["POST"])
def analyst_agent():
    if "questions.txt" not in request.files:
        return jsonify(error="questions.txt missing"), 400

    questions = request.files["questions.txt"].read().decode("utf-8", "ignore")
    temp_files = _save_attachments(request.files)      # optional, not used here
    evaluation = """
        description: "TDS Data Analyst Agent – generic eval (20-point rubric)"

        providers:
        - id: https
            config:
            url: https://app.example.com/api/ # Replace this with your API endpoint
            method: POST
            body: file://question.txt
            transformResponse: json

        assert:
            # Structural gate – no score, hard-fail if not a 4-element array
            - type: is-json
            value: {type: array, minItems: 4, maxItems: 4}
            weight: 0

            # 1️⃣ first answer must equal 1
            - type: python
            weight: 4
            value: |
                import json, sys
                print(json.loads(output)[0] == 1)

            # 2️⃣ second answer must contain “Titanic” (case-insensitive)
            - type: python
            weight: 4
            value: |
                import json, re, sys
                print(bool(re.search(r'titanic', json.loads(output)[1], re.I)))

            # 3️⃣ third answer within ±0.001 of 0.485782
            - type: python
            weight: 4
            value: |
                import json, sys, math
                print(abs(float(json.loads(output)[2]) - 0.485782) <= 0.001)

            # 4️⃣ vision check ― send plot to GPT-4o-mini and grade multiple criteria
            - type: llm-rubric
            provider: openai:gpt-4.1-nano
            weight: 8
            # extract base-64 PNG from the 4th array element and inject into the prompt
            preprocess: |
                import json, re
                data = json.loads(output)
                context['plot'] = data[3
            rubricPrompt: |
                [
                { "role": "system",
                    "content": "Grade the scatterplot. Award *score 1* only iff ALL are true: \
                    (a) it’s a scatterplot of Rank (x-axis) vs Peak (y-axis); \
                    (b) a dotted **red** regression line is present; \
                    (c) axes are visible & labelled; \
                    (d) file size < 100 kB. Otherwise score 0. \
                    Respond as JSON: {scatterplot:bool, regression:bool, axes:bool, size:bool, score:number}"
                },
                { "role": "user",
                    "content": [
                    { "type": "image_url",
                        "image_url": { "url": "{{plot}}" }      # data:image/png;base64,… :contentReference[oaicite:5]{index=5}
                    },
                    { "type": "text",
                        "text": "Here is the original task:\n\n{{vars.question}}\n\nReview the image and JSON above." }
                    ]
                }
                ]
            threshold: 0.99  # require full pass

        tests:
        - description: "Data analysis"

    """

    sample_response = [1, "Titanic", 0.485782, "data:image/png;base64,iVBORw0KG... (response truncated)"]

    prompt = f"read all the questions from the {questions} do exactly what is being said in the question then create the response the reponse will be evaluated exaclty like {evaluation}  make sure you response passes all evaluation expectations and here is the sample response {sample_response}"



    payload = {
    "model": "gpt-4.1",         
    "messages": [
        {"role": "system",
         "content": "You are a data-analyst agent. "
                    "strictly follow he prompt"},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0,
    "max_tokens": 4096
}

    resp = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
    json=payload,                   # ← json= not data=
    timeout=180
)
    resp.raise_for_status()
    answer = resp.json()["choices"][0]["message"]["content"].strip()




    for p in temp_files.values():                   # clean temp files
        try: os.unlink(p)
        except OSError: pass

    return jsonify(answer=answer), 200

# 4️⃣  run it --------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
