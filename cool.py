import streamlit as st
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


def process_array(array):
    print(array)


def get_storage_links(url):
    requests = []

    def add_url(url):
        if urlparse(url.url).hostname == "storage.googleapis.com":
            requests.append(url.url)

    with sync_playwright() as p:
        h_name = "storage.googleapis.com"
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.on("request", add_url)
        page.goto(url)
        page.wait_for_event("request", lambda request: h_name == urlparse(request.url).hostname)
        browser.close()
    
    return requests[-1]

print(get_storage_links("https://www.dronedeploy.com/app2/sites/667f19762172612132175cf2/preprocessed-pano/667f198121726121321764a5/assets/667f19882172612132176fdc?jwt_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpZCI6IjY2N2YxOTgwMjE3MjYxMjEzMjE3NjQ4MyIsInR5cGUiOiJQdWJsaWNTaGFyZVYyIiwiYWNjZXNzX3R5cGUiOiJzaW5nbGVNZWRpYSIsImFzc2V0X2lkIjoiNjY3ZjE5ODgyMTcyNjEyMTMyMTc2ZmRjIn0.F_6Ev399zkEalMi4B3Iml3f_XBU6U8FasRZFQXFP5N2liSeZ0LDc44apV6AF461h8_ADHo_v46APYrIcq_YBAA"))

# import asyncio
# import nodriver as uc

# async def main():
#     browser = await uc.start()
#     page = await browser.get('https://www.nowsecure.nl')

#     await page.save_screenshot()
#     await page.get_content()
#     await page.scroll_down(150)
#     elems = await page.select_all('*[src]')
#     for elem in elems:
#         await elem.flash()

#     page2 = await browser.get('https://twitter.com', new_tab=True)
#     page3 = await browser.get('https://github.com/ultrafunkamsterdam/nodriver', new_window=True)

#     for p in (page, page2, page3):
#        await p.bring_to_front()
#        await p.scroll_down(200)
#        await p   # wait for events to be processed
#        await p.reload()
#        if p != page3:
#            await p.close()


# if __name__ == '__main__':

#     # since asyncio.run never worked (for me)
#     uc.loop().run_until_complete(main())





# try:
#     from nodriver import start, cdp, loop
# except (ModuleNotFoundError, ImportError):
#     import sys, os

#     sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
#     from nodriver import start, cdp, loop


# async def main():
#     browser = await start()

#     tab = browser.main_tab
#     tab.add_handler(cdp.network.RequestWillBeSent, send_handler)

#     tab = await browser.get("https://www.dronedeploy.com/app2/sites/667f19762172612132175cf2/preprocessed-pano/667f198121726121321764a5/assets/667f19882172612132176fdc?jwt_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpZCI6IjY2N2YxOTgwMjE3MjYxMjEzMjE3NjQ4MyIsInR5cGUiOiJQdWJsaWNTaGFyZVYyIiwiYWNjZXNzX3R5cGUiOiJzaW5nbGVNZWRpYSIsImFzc2V0X2lkIjoiNjY3ZjE5ODgyMTcyNjEyMTMyMTc2ZmRjIn0.F_6Ev399zkEalMi4B3Iml3f_XBU6U8FasRZFQXFP5N2liSeZ0LDc44apV6AF461h8_ADHo_v46APYrIcq_YBAA")

#     await tab.sleep(10)




# async def send_handler(event: cdp.network.RequestWillBeSent):
#     r = event.request
#     s = f"{r.method} {r.url}"
#     for k, v in r.headers.items():
#         s += f"\n\t{k} : {v}"
#     print(s)


# if __name__ == "__main__":
#     loop().run_until_complete(main())