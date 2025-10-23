from flask import Flask, request, jsonify
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from dotenv import load_dotenv
from io import BytesIO
import base64
import os
import re

app = Flask(__name__)
load_dotenv()

# Azure credentials
endpoint = os.getenv("AZURE_AI_DOC_INTEL_EP")
key = os.getenv("AZURE_AI_DOC_INTEL_KEY")

document_intelligence_client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

# Your existing parsing function
from parse_logic import parse_production_card  # move your function to parse_logic.py

@app.route("/analyze", methods=["POST"])
def analyze_pdf():
    try:
        data = request.get_json()
        base64_pdf = data.get("pdf_base64")

        if not base64_pdf:
            return jsonify({"error": "Missing 'pdf_base64' in request"}), 400

        pdf_bytes = base64.b64decode(base64_pdf)
        pdf_stream = BytesIO(pdf_bytes)

        poller = document_intelligence_client.begin_analyze_document(
            model_id="prebuilt-read",
            content_type="application/pdf",
            analyze_request=pdf_stream
        )
        result: AnalyzeResult = poller.result()
        result_dict = result.as_dict()

        parsed = parse_production_card(result_dict["content"])
        return jsonify({"parsed_result": parsed})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)