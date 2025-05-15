import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
import yt_dlp
import uuid
import shutil
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)

logging.basicConfig(level=logging.INFO)

DOWNLOAD_FOLDER = os.path.join(app.root_path, 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.form.get('videoUrl')
    if not video_url:
        flash('الرجاء إدخال رابط الفيديو.', 'error')
        return redirect(url_for('index'))

    unique_id = str(uuid.uuid4())
    output_subfolder = os.path.join(DOWNLOAD_FOLDER, unique_id)
    os.makedirs(output_subfolder, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(output_subfolder, '%(title)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',  # Attempt to download pre-merged mp4 or best available single file
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'nocheckcertificate': True,
        'logtostderr': False,
        'progress_hooks': [lambda d: app.logger.info(f"yt-dlp progress: {d}")],
    }

    try:
        app.logger.info(f"Attempting to download: {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            downloaded_files = os.listdir(output_subfolder)
            if not downloaded_files:
                flash('فشل تحميل الفيديو. لم يتم العثور على الملف بعد المعالجة.', 'error')
                if os.path.exists(output_subfolder):
                    shutil.rmtree(output_subfolder)
                return redirect(url_for('index'))
            
            filename = downloaded_files[0]
            flash(f'تم تحميل الفيديو بنجاح: {filename}', 'success')
            return redirect(url_for('serve_file', unique_id=unique_id, filename=filename))

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        app.logger.error(f"DownloadError for {video_url}: {error_message}")
        user_friendly_message = f'حدث خطأ أثناء محاولة تحميل الفيديو.'

        if "Sign in to confirm you're not a bot" in error_message or "cookies" in error_message.lower():
            user_friendly_message = 'يتطلب هذا الفيديو تسجيل الدخول أو استخدام ملفات تعريف الارتباط (cookies) للتحميل. هذه الميزة غير مدعومة حاليًا.'
        elif "Unsupported URL" in error_message:
            user_friendly_message = 'الرابط الذي أدخلته غير مدعوم.'
        elif "Video unavailable" in error_message:
            user_friendly_message = 'هذا الفيديو غير متاح أو خاص.'
        elif "No video could be found" in error_message:
            user_friendly_message = 'لم يتم العثور على فيديو في الرابط المقدم.'
        elif "Cannot parse data" in error_message:
            user_friendly_message = 'حدث خطأ أثناء تحليل بيانات الفيديو من المصدر. قد يكون الرابط غير صحيح أو أن هناك مشكلة مؤقتة في المصدر.'
        else:
            user_friendly_message = f'فشل تحميل الفيديو. الخطأ: {error_message.split("ERROR:", 1)[-1].strip()}'
        
        flash(user_friendly_message, 'error')
        if os.path.exists(output_subfolder):
             shutil.rmtree(output_subfolder)
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"General Error for {video_url}: {str(e)}")
        flash(f'حدث خطأ عام غير متوقع: {str(e)}', 'error')
        if os.path.exists(output_subfolder):
            shutil.rmtree(output_subfolder)
        return redirect(url_for('index'))

@app.route('/downloads/<unique_id>/<filename>')
def serve_file(unique_id, filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, unique_id)
    try:
        return send_from_directory(file_path, filename, as_attachment=True)
    except FileNotFoundError:
        flash('لم يتم العثور على الملف المطلوب للتحميل.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)

