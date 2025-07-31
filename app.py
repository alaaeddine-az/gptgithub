import os
import requests
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

# Configurations
ACCESS_TOKEN = os.environ.get('FB_ACCESS_TOKEN')
AD_ACCOUNT_ID = os.environ.get('FB_AD_ACCOUNT_ID')  # Format: 'act_<ID>'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class AdMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(128))
    media_type = db.Column(db.String(32))
    start_date = db.Column(db.String(32))
    end_date = db.Column(db.String(32))
    file_path = db.Column(db.String(256))
    ad_id = db.Column(db.String(64))

# Initialize DB
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    brand = request.form['brand']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    media_type = request.form['media_type']

    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        return 'Configurez FB_ACCESS_TOKEN et FB_AD_ACCOUNT_ID', 500

    FacebookAdsApi.init(access_token=ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    fields = ['id', 'adcreatives']
    params = {
        'time_range': {'since': start_date, 'until': end_date},
        'effective_status': ['ACTIVE', 'ARCHIVED'],
    }

    ads = account.get_ads(fields=fields, params=params)

    for ad in ads:
        creatives = ad['adcreatives']
        for creative in creatives:
            creative_id = creative['id']
            creative_data = AdAccount(AD_ACCOUNT_ID).get_ad_creatives(
                fields=['object_story_spec'], params={'id': creative_id}
            )
            story = creative_data[0].get('object_story_spec', {})
            attachments = (
                story.get('video_data')
                or story.get('link_data')
                or story.get('image_data')
            )
            if not attachments:
                continue

            media_url = attachments.get('url') or attachments.get('video_url')
            file_path = None
            if media_url:
                os.makedirs('media', exist_ok=True)
                file_name = f"{ad['id']}_{os.path.basename(media_url)}"
                file_path = os.path.join('media', file_name)
                try:
                    resp = requests.get(media_url)
                    with open(file_path, 'wb') as f:
                        f.write(resp.content)
                except Exception:
                    file_path = None

            entry = AdMedia(
                brand=brand,
                media_type=media_type,
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                ad_id=ad['id'],
            )
            db.session.add(entry)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
