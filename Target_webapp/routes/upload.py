from flask import Blueprint, request, render_template
import os
import app.config as config

upload_bp = Blueprint('upload', __name__)

# Absolute path resolved relative to this file so the app works regardless
# of the working directory it is launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(_HERE, '..', 'static', 'uploads')

# Ensure the directory exists at startup — prevents 500 on first upload.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():

    message = ""

    if request.method == 'POST':

        # Guard: file field missing from request
        if 'file' not in request.files or request.files['file'].filename == '':
            return """
            <h2 style='color:red;text-align:center;margin-top:100px;'>
            ❌ No file selected
            </h2>
            """

        file = request.files['file']

        # =========================================
        # SECURE MODE
        # =========================================

        if config.INPUT_SANITIZATION_ENABLED:

            # Allow only image files
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):

                return """
                <h2 style='color:red;text-align:center;margin-top:100px;'>
                ❌ Only image files allowed
                </h2>
                """

        # =========================================
        # VULNERABLE MODE (or image passed validation)
        # =========================================

        try:
            dest = os.path.join(UPLOAD_FOLDER, os.path.basename(file.filename))
            file.save(dest)
            message = "✅ File Uploaded Successfully"
        except Exception as exc:
            return f"""
            <h2 style='color:red;text-align:center;margin-top:100px;'>
            ❌ Upload failed: {exc}
            </h2>
            """

    return render_template(
        'upload.html',
        message=message
    )