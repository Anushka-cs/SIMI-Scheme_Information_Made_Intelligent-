from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# --- Load schemes from JSON ---
# Changed the file name from "schemes_fixed_cleaned.json" to "schemes_final.json"
with open("schemes_final.json", "r", encoding="utf-8") as f:
    schemes_data = json.load(f)

# --- Helper functions ---
def normalize(text):
    return text.lower().strip() if isinstance(text, str) else ""

def is_match(user_value, scheme_value):
    user_value = normalize(user_value)
    scheme_value = normalize(scheme_value)
    return user_value in scheme_value or scheme_value in user_value

def is_education_match(user_edu, scheme_edu):
    user_edu = normalize(user_edu)
    scheme_edu = normalize(scheme_edu)

    synonyms = {
        "class 12": ["class 12", "12th", "xii", "post-matric", "class 11 onwards", "higher secondary"],
        "class 11": ["class 11", "xi", "post-matric"],
        "phd": ["ph.d", "phd", "doctorate", "research", "registered in a phd", "ph.d candidates"],
        "graduate": ["graduation", "undergraduate", "bachelor", "b.a", "b.sc", "b.tech", "b.com", "enrolled in university"],
        "postgraduate": ["postgraduation", "post-graduate", "master", "m.a", "m.sc", "m.tech", "m.com"],
    }

    for synonym in synonyms.get(user_edu, [user_edu]):
        if synonym in scheme_edu:
            return True

    return user_edu in scheme_edu or scheme_edu in user_edu

# --- Webhook route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json()

    # 🔍 Log full request
    print("\n📥 Incoming Dialogflow Request:")
    print(json.dumps(req, indent=2))

    # 📌 Extract and log parameters
    params = req.get("queryResult", {}).get("parameters", {})
    print("\n📌 Extracted Parameters:")
    print(json.dumps(params, indent=2))

    user_caste = normalize(params.get("caste", ""))
    user_gender = normalize(params.get("gender", ""))
    user_education = normalize(params.get("education", ""))

    matched_schemes = []

    for scheme in schemes_data:
        if not isinstance(scheme, dict) or len(scheme) == 0:
            continue

        # 🏷️ Scheme title fallback logic
        title = (
            scheme.get("Scheme Title") or 
            scheme.get("scheme_name") or 
            scheme.get("title") or 
            scheme.get("Description") or 
            (normalize(scheme.get("eligibility", ""))[:50] + "...") if scheme.get("eligibility") else 
            "Unnamed Scheme"
        )

        if "unnamed scheme" in title.lower():
            print("🚨 Skipping scheme with no usable title:")
            print(json.dumps(scheme, indent=2))
            continue

        print(f"\n🔎 Checking Scheme: {title}")

        # Target fields
        target = scheme.get("Target Beneficiaries", {}) or {}
        caste_field = normalize(
            target.get("Caste") or
            scheme.get("target_group") or
            scheme.get("Caste") or
            scheme.get("beneficiaries") or ""
        )
        gender_field = normalize(
            target.get("Gender") or
            scheme.get("Gender") or ""
        )
        education_field = normalize(
            target.get("Education") or
            scheme.get("Education") or ""
        )

        # Eligibility (flatten if dict)
        eligibility_raw = (
            scheme.get("eligibility") or 
            scheme.get("Eligibility") or 
            ""
        )
        if isinstance(eligibility_raw, dict):
            eligibility_text = normalize(" ".join(str(v) for v in eligibility_raw.values()))
        else:
            eligibility_text = normalize(eligibility_raw)

        # Log fields
        print(f" - Caste: User={user_caste} | Scheme={caste_field}")
        print(f" - Gender: User={user_gender} | Scheme={gender_field}")
        print(f" - Education: User={user_education} | Scheme={education_field}")
        print(f" - Eligibility text: {eligibility_text[:80]}...")

        # Matching
        caste_match = is_match(user_caste, caste_field) or is_match(user_caste, eligibility_text)
        gender_match = True
        if gender_field or "female" in eligibility_text or "male" in eligibility_text:
            gender_match = is_match(user_gender, gender_field) or is_match(user_gender, eligibility_text)
        education_match = (
            is_education_match(user_education, education_field) or
            is_education_match(user_education, eligibility_text)
        )

        print(f"    → Matches: Caste={caste_match}, Gender={gender_match}, Education={education_match}")

        if caste_match and gender_match and education_match:
            print("✅ Scheme matched.")
            matched_schemes.append({
                "title": title,
                "ministry": scheme.get("ministry") or scheme.get("Department / Ministry", "Not specified"),
                "benefits": scheme.get("benefits") or scheme.get("Benefits", "Not specified"),
                "eligibility": eligibility_text or "Not specified",
                "application_link": scheme.get("Application Link", "Not specified")
            })
        else:
            print("❌ Not matched.")

    print(f"\n✅ Total matched schemes: {len(matched_schemes)}")

    # --- Format response ---
    if matched_schemes:
        response_lines = ["✅ You are eligible for the following schemes:"]
        for s in matched_schemes:
            response_lines.append(f"\n🔹 {s['title']}")
            response_lines.append(f"   • 🏛️ Ministry: {s['ministry']}")
            response_lines.append(f"   • 🎯 Benefits: {s['benefits']}")
            response_lines.append(f"   • 📄 Eligibility: {s['eligibility']}")
            response_lines.append(f"   • 🔗 Apply Here: {s['application_link']}")
        response_text = "\n".join(response_lines)
    else:
        response_text = "❌ Sorry, no schemes matched your profile."

    return jsonify({"fulfillmentText": response_text})

# --- Run server ---
if __name__ == '__main__':
    app.run(port=5000)