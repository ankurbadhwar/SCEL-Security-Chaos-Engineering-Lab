from flask import Blueprint, request, render_template
import os
import app.config as config

upload_bp = Blueprint('upload', __name__)

UPLOAD_FOLDER = "app/static/uploads"


@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():

    message = ""

    if request.method == 'POST':

        file = request.files['file']

        # =========================================
        # SECURE MODE
        # =========================================

        if config.INPUT_SANITIZATION_ENABLED:

            # Allow only image files
            if not file.filename.endswith(('.png', '.jpg', '.jpeg')):

                return """
                <h2 style='color:red;text-align:center;margin-top:100px;'>
                ❌ Only image files allowed
                </h2>
                """

        # =========================================
        # VULNERABLE MODE
        # =========================================

        file.save(
            os.path.join(
                UPLOAD_FOLDER,
                file.filename
            )
        )

        message = "✅ File Uploaded Successfully"

    return render_template(
        'upload.html',
        message=message
    )