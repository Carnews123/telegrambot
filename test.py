import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

# ==== CONFIG ====
TOKEN = "7971875382:AAHaumWs61DY5l9ncbwhhB09GNeKHY2jxNE"
CHROME_DRIVER_PATH = "/home/mamed050/Desktop/python=projects/projects/newbinaz/chromedriver"
DISTRICTS = [
    "Yasamal r.", "Suraxanı r.", "Səbail r.", "Sabunçu r.", "Pirallahı r.",
    "Nizami r.", "Nəsimi r.", "Nərimanov r.", "Qaradağ r.", "Xəzər r.",
    "Xətai r.", "Binəqədi r.", "Abşeron r."
]
user_selections = {}  # Store selected districts per user

# ==== SELENIUM ====
def get_driver():
    service = Service(executable_path=CHROME_DRIVER_PATH)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("user-agent=Mozilla/5.0 Chrome/114.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=service, options=options)

def extract_listings():
    driver = get_driver()
    driver.get("https://bina.az")
    time.sleep(7)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    container = soup.find("div", class_="sc-b92fa7fa-0 dxZwLp")
    unique_links = []
    if container:
        links = container.find_all("a", href=True)
        for link in links:
            href = link["href"]
            full_url = f"https://bina.az{href}"
            if full_url not in unique_links:
                unique_links.append(full_url)
    return unique_links[:3]  # Get latest 3 listings

def scrape_listing(url):
    driver = get_driver()
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    owner_div = soup.find("div", class_="product-owner__info-region")
    if not owner_div or owner_div.text.strip().lower() != "mülkiyyətçi":
        return None

    ul = soup.find("ul", class_="product-extras bz-d-flex bz-align-center bz-gap-15 bz-wrap-wrap")
    if ul:
        for li in ul.find_all("li", class_="product-extras__i"):
            a_tag = li.find("a")
            if a_tag:
                return {"url": url, "district": a_tag.text.strip()}
    return None

# ==== TELEGRAM HANDLERS ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔁 Bütün Elanlar", callback_data="ALL")],
        *[
            [InlineKeyboardButton(d, callback_data=d)] for d in DISTRICTS
        ],
        [InlineKeyboardButton("✅ Seçimi Bitir", callback_data="done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user_selections[update.effective_user.id] = []
    await update.message.reply_text("📍 Əraziləri seçin:", reply_markup=reply_markup)

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "done":
        selections = user_selections.get(user_id, [])
        await query.edit_message_text(
            f"✅ Seçilmiş ərazilər: {', '.join(selections) if selections else 'Bütün Elanlar'}"
        )
        await check_bina_and_send(update, context, selections)
    elif data == "ALL":
        user_selections[user_id] = "ALL"
        await query.edit_message_text("🔁 Bütün yeni elanlar yoxlanılacaq.")
        await check_bina_and_send(update, context, "ALL")
    else:
        # Add or toggle selection
        selections = user_selections.get(user_id, [])
        if data not in selections:
            selections.append(data)
        else:
            selections.remove(data)
        user_selections[user_id] = selections

async def check_bina_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, selection):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔍 Yeni elanlar axtarılır...")
    seen = set()
    listings = extract_listings()
    found = []

    for url in listings:
        if url in seen:
            continue
        listing = scrape_listing(url)
        if listing:
            seen.add(url)
            if selection == "ALL" or listing["district"] in selection:
                found.append(f"📍 <b>{listing['district']}</b>\n🔗 {listing['url']}")

    if found:
        for msg in found:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Heç bir uyğun elan tapılmadı.")

# ==== RUN APP ====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_selection))
    print("🤖 Bot hazırdır...")
    app.run_polling()

if __name__ == "__main__":
    main()
