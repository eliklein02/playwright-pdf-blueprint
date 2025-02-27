import streamlit as st

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import AnnotationBuilder, FloatObject

import random
import base64
import json
import concurrent.futures
from datetime import datetime
import os
import io
from dotenv import load_dotenv
import asyncio


from playwright.async_api import async_playwright

from urllib.parse import quote
from urllib.parse import urlparse
import time
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

os.system("playwright install")

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
    st.error("Error finding credentials file. Please contact the developer.")

new_annots = []
annotation_count = 0
processed_annotations = 0
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


async def pdf_iter(file):
    global annotation_count
    st.write("Started Process...")
    count = 0
    reader = PdfReader(file)
    writer = PdfWriter()
    annotations = []
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        if "/Annots" in page:
            for a in page["/Annots"]:
                if count >= 30:
                    break
                link = a["/A"]["/URI"]
                rect = a["/Rect"]
                annot = {
                    "url": link,
                    "rect": rect,
                    "page": i
                }
                annotations.append(annot)
                count = count + 1
                annotation_count = len(annotations)
            st.write(f"Found {annotation_count} annotations.")
            del page["/Annots"]
            writer.add_page(page)
    today = datetime.today()
    day_name = today.strftime('%A')
    time = today.strftime('%I:%M %p')
    c = day_name + "-" + str(today).split(" ")[0] + "-" + time
    parent_folder = create_folder(c, "1JtiUFBlXchgibYyMVTBLmWqSrvrapptg")
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

    new = await rate_limited(annotations, viewable_images_folder)
    
    await close_browser()
    print(f"new: {new}")
    for i in new:
        print(new)
        print(i)
        page = reader.pages[i[0]]
        rect = i[1]
        name = i[2]
        a = AnnotationBuilder.link(
            rect=(rect[0], rect[1], rect[2], rect[3]),
            url=name + ".html",
        )
        writer.add_annotation(page_number=i[0], annotation=a)
    

    with open("output.pdf", "wb") as output_pdf:
        writer.write(output_pdf)

    upload_file("./output.pdf", "application/pdf", folder_id=viewable_images_folder)

    os.remove("./output.pdf")

    st.info("Process Completed.")
    st.write("https://drive.google.com/drive/folders/1JtiUFBlXchgibYyMVTBLmWqSrvrapptg?usp=sharing")
    st.balloons()

        
async def rate_limited(array, folder, limit=2):
    to_return = []
    count = 0
    chunks = array[count:count + limit]
    for i in range(0, len(array), limit):
        chunks = array[i:i + limit]
    #     with concurrent.futures.ProcessPoolExecutor() as e:
    #         new = await list(e.map(process_annotation_wrapper, [(a, folder) for a in chunks]))
    #         to_return.extend(new)
    # return to_return
        tasks = [process_annotation_wrapper((a, folder)) for a in chunks]
        print(f"Tasks: {tasks}")
        results = await asyncio.gather(*tasks)
        results = list(results)
        to_return.extend(results)
    return to_return

def process_annotation_wrapper(args):
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

# async def extract_googleapis_link(url):
#     global browser, context
#     await launch_browser()

#     requests = []

#     async def add_url(url):
#         if urlparse(url.url).hostname == "storage.googleapis.com":
#             requests.append(url.url)

#     while len(requests) == 0:
#         async with async_playwright() as p:
#             h_name = "storage.googleapis.com"
#             page = await context.new_page()
#             await page.on("request", await add_url)
#             await page.goto(url)
#             await page.wait_for_event("request", lambda request: h_name == urlparse(request.url).hostname)


#     payload = {
#         "url": requests[-1],
#         "name": requests[-1].split("/")[5].split(".")[0]
#     }
    
#     return payload
# ... (other imports and code)

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
        await page.goto(url)
        page.on("request", lambda request: add_url(request))
        try:
            await page.wait_for_event("request", lambda request: urlparse(request.url).hostname == "storage.googleapis.com")
        except Exception as e:
            print(f"Error: {e} for url: {url}")
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
        st.write("Error:")
        st.write(e)
        st.write("Please try again.")
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
        st.write("Error:")
        st.write(e)
        st.write("Please try again.")
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


async def main():
    uploaded = st.file_uploader("Please upload a pdf")

    if uploaded is not None:
        button = st.button("Start")
        if button:
            random_number = random.randint(100, 1000000)
            random_number = str(random_number)
            bytes_data = uploaded.getvalue()
            file_name = uploaded.name.split(".")[0]
            file_extension = uploaded.name.split(".")[1]
            try:
                await pdf_iter(file_name + "." + file_extension)
            except Exception as e:
                st.write("Error:")
                st.write(e)
                st.write("Please try again.")

if __name__ == "__main__":
    asyncio.run(main())