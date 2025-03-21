from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import AnnotationBuilder, FloatObject

import base64
from datetime import datetime
import os
import io
from dotenv import load_dotenv
import asyncio
import sys
from urllib.parse import urlparse
import time
import requests


from playwright.async_api import async_playwright
import sendgrid
from sendgrid.helpers.mail import *
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

# os.system("playwright install")

try:
    load_dotenv()
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT = {
        "type": os.getenv("GOOGLE_CLOUD_TYPE"),
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_CLOUD_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_CLOUD_PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("GOOGLE_CLOUD_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLOUD_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_CLOUD_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_CLOUD_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_CLOUD_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLOUD_CLIENT_X509_CERT_URL")
    }
    credentials = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
except Exception as e:
    print("Error finding credentials file. Please contact the developer.")
    sys.stdout.flush()

new_annots = []

browser = None
context = None
page = None

async def launch_browser():
    global browser, context, page
    if not browser:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

async def close_browser():
    global browser
    if browser:
        await browser.close()
        browser = None

async def pdf_iter(file, folder_name, file_bytes, limit):
    count = 0
    print(f"Processing file: {file}")
    if limit == "zero":
        print("Its zero")
        limit = 0
    else:
        print("Not z")
        limit = int(limit) - 1
    sys.stdout.flush()
    processed_annotations = 0
    file_stream = io.BytesIO(file_bytes)
    reader = PdfReader(file_stream)
    writer = PdfWriter()
    annotations = []
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        if "/Annots" in page:
            for a in page["/Annots"]:
                if count > limit and limit != 0:
                    break
                link = a["/A"]["/URI"]
                rect = a["/Rect"]
                annot = {
                    "url": link,
                    "rect": rect,
                    "page": i
                }
                annotations.append(annot)
                annotation_count = len(annotations)
                count = count + 1
            print(f"Found {annotation_count} annotations.")
            sys.stdout.flush()
            del page["/Annots"]
            writer.add_page(page)
    parent_folder = create_folder(folder_name, "1JtiUFBlXchgibYyMVTBLmWqSrvrapptg")
    viewable_images_folder = create_folder("360 Images", parent_id=parent_folder)
    required_assets_folder = create_folder("required_assets", parent_id=viewable_images_folder)
    current_dir = os.getcwd()
    required_assets_folder_local = os.path.join(current_dir + "/required_assets")
    files_in_r_a = os.listdir(required_assets_folder_local)
    for a in files_in_r_a:
        if a.split(".")[1] == "css":
            mime_type = "text/css"
        else:
            mime_type = "text/javascript"
        upload_file(f"./required_assets/{a}", mime_type, folder_id=required_assets_folder)
    try:
        new = await rate_limited(annotations, viewable_images_folder)
        for i in new:
            page = reader.pages[i[0]]
            rect = i[1]
            name = i[2]
            a = AnnotationBuilder.link(
                rect=(rect[0], rect[1], rect[2], rect[3]),
                url="360 Images/" + name + ".html",
            )
            writer.add_annotation(page_number=i[0], annotation=a)
        

        with open(file, "wb") as output_pdf:
            writer.write(output_pdf)

        upload_file(f"./{file}", "application/pdf", folder_id=parent_folder)

        os.remove(f"./{file}")

        print("Done")
        sys.stdout.flush()
    finally:
        await close_browser()
        return parent_folder

        
async def rate_limited(array, folder, limit=10):
    to_return = []
    count = 0
    chunks = array[count:count + limit]
    for i in range(0, len(array), limit):
        chunks = array[i:i + limit]
        tasks = [process_annotation_wrapper((a, folder)) for a in chunks]
        print(f"Tasks: {tasks}")
        sys.stdout.flush()
        results = await asyncio.gather(*tasks)
        results = list(results)
        to_return.extend(results)
    return to_return

def process_annotation_wrapper(args):
    print("Starting process annotation...")
    sys.stdout.flush()
    a, folder = args
    return process_annotation(a, folder)


async def process_annotation(a, folder):
    try:
        link = a['url']
        rect = a['rect']
        page = a['page']
    except KeyError:
        link = a['url']
        rect = a['rect']
        page = a['page']
    payload = await extract_googleapis_link(link)
    try:
        url = payload['url']
        name = payload['name']
    except KeyError:
        payload = await extract_googleapis_link(link)
        url = payload['url']
        name = payload['name']
    image_data = get_image_from_storage(url, link)
    process_img_data(image_data, name, folder)
    return [page, rect, name]

async def extract_googleapis_link(url):
    global browser, context
    if not browser or not context:
        await launch_browser()
    requests = []

    def add_url(url):
        if urlparse(url.url).hostname == "storage.googleapis.com":
            requests.append(url.url)

    while len(requests) == 0:
        page = await context.new_page()
        await page.goto(url, timeout=60000)
        page.on("request", lambda request: add_url(request))
        try:
            await page.wait_for_event("request", lambda request: urlparse(request.url).hostname == "storage.googleapis.com")
        except Exception as e:
            print(f"Error: {e} for url: {url}")
        finally:
            await page.close()
    payload = {
        "url": requests[-1],
        "name": requests[-1].split("/")[5].split(".")[0]
    }
    
    return payload


def get_image_from_storage(img_url, ref):
    headers = {
        'Accept': 'image/*,*/*;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://www.dronedeploy.com',
        'Pragma': 'no-cache',
        'Referer': ref,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'X-Client-Data': 'CJe2yQEIprbJAQipncoBCKaRywEIk6HLAQid/swBCIagzQEIkN/OARiPzs0B',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    response = requests.get(img_url, headers=headers)
    return response._content

def process_img_data(img_data, name, folder):
        html_content = f"""
        <html>
        <head>
            <title>360 Image</title>
            <meta name="description" content="Display a single-resolution cubemap image." />
            <meta name="viewport" content="target-densitydpi=device-dpi, width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no, minimal-ui" />
            <style>
            @-ms-viewport {{ width: device-width; }}
            </style>
            <link rel="stylesheet" href="./required_assets/reset.css">
            <link rel="stylesheet" href="./required_assets/style.css">
        </head>
        <body>
            <div id="pano"></div>
            <script src="./required_assets/es5-shim.js"></script>
            <script src="./required_assets/eventShim.js"></script>
            <script src="./required_assets/requestAnimationFrame.js" ></script>
            <script src="./required_assets/marzipano.js" ></script>
            <script>
                var img_data = "data:image/jpeg;base64,{base64.b64encode(img_data).decode('utf-8')}";
            </script>
            <script src="./required_assets/index.js"></script>
        </body>
        </html>
        """
        name = f"{name}.html"
        file = io.BytesIO(html_content.encode('utf-8'))
        res = html_file_upload(file, name, folder)

        print("Upload done.")
        sys.stdout.flush()
def create_folder(name, parent_id=None):
    folder_metadata = {
        "name": name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    if parent_id:
        folder_metadata["parents"] = [parent_id]

    try:
        folder = service.files().create(body=folder_metadata, fields="id").execute()
    except Exception as e:
        print("Error:")
        print(e)
        print("Please try again.")
        sys.stdout.flush()
        return
    return folder.get("id")

def upload_file(file_path, mime_type, folder_id=None):
    name = file_path.split("/")[-1]
    file_metadata = { "name": name }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    try:
        media = MediaFileUpload(file_path, mimetype=mime_type)
        file = service.files().create(body = file_metadata, media_body = media, fields = "id", ).execute()
    except Exception as e:
        time.sleep(3)
        file = service.files().create(body = file_metadata, media_body = media, fields = "id", ).execute()
        return
    return file

def html_file_upload(file, name, folder):
    file_metadata = {
        "name": name,
        "parents": [folder]
    }

    media = MediaIoBaseUpload(file, mimetype="text/html", resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file

def send_email(to, subject, content):
    sg = sendgrid.SendGridAPIClient(api_key=(os.getenv("SENDGRID_API_KEY")))
    from_email = Email("info@192dnsserver.com")
    to_email = to
    subject = subject
    content = Content("text/plain", content)
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    print(response.status_code)
    sys.stdout.flush()

async def main():
    print(sys.argv)
    sys.stdout.flush()
    file_name = sys.argv[1]
    file_path_in_tmp = sys.argv[2]
    folder_name = sys.argv[3]
    limit = sys.argv[4]
    with open(file_path_in_tmp, "rb") as f:
        bytes_data = f.read()
    try:
        funct = await pdf_iter(file_name, folder_name, bytes_data, limit)
        sys.stdout.flush()
        send_email("info@innerview-cpd.com", "Your script is done!", f"Your script has finished running. \nHere is the link: https://drive.google.com/drive/folders/{funct}?usp=sharing")
    except Exception as e:
        send_email("eliklein02@gmail.com", "Error while running script", f"An error occured. \n\n {e}")
        send_email("info@innerview-cpd.com", "Error while running script", f"Please try again. The developer was notified and will look into this soon.")
        print(f"Error processing PDF: {e}")
        sys.stdout.flush()
    finally:
        if browser:
            await close_browser()

if __name__ == "__main__":
    asyncio.run(main())