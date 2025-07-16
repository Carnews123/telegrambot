import asyncio
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

TOKEN = "7971875382:AAHaumWs61DY5l9ncbwhhB09GNeKHY2jxNE"
CHROME_DRIVER_PATH = "/home/mamed050/Desktop/python=projects/projects/newbinaz/chromedriver"

DISTRICTS = [
    "Yasamal r.", "Suraxanı r.", "Səbail r.", "Sabunçu r.", "Pirallahı r.",
    "Nizami r.", "Nəsimi r.", "Nərimanov r.", "Qaradağ r.", "Xəzər r.",
    "Xətai r.", "Binəqədi r.", "Abşeron r."
]

user_tasks = {}
user_selected_districts = {}  # Store multiple selections per user

# ---------------------- SCRAPER FUNCTIONS -----------------------

def get_driver():
    service = Service(executable_path=CHROME_DRIVER_PATH)
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--headless=new')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=service, options=options)

def extract_listings():
    driver = get_driver()
    driver.get("https://bina.az")
    time.sleep(5)
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

    return unique_links[:5]

def scrape_listing(url):
    driver = get_driver()
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    owner_div = soup.find("div", class_="product-owner__info-region")
    if not owner_div or owner_div.text.strip().lower() != "mülkiyyətçi":
        return None

    ul = soup.find("ul", class_="product-extras bz-d-flex bz-align-center bz-gap-15 bz-wrap-wrap")
    if ul:
        li_tags = ul.find_all("li", class_="product-extras__i")
        for li in li_tags:
            a_tag = li.find("a")
            if a_tag:
                district = a_tag.text.strip()
                return {"url": url, "district": district}
    return None

# ---------------------- BACKGROUND SCRAPER -----------------------

async def continuous_scrape(chat_id: int, bot, selected_districts):
    seen_urls = set()
    await bot.send_message(chat_id=chat_id, text=f"📡 Axtarış başladı: {', '.join(selected_districts)}")

    while True:
        all_urls = extract_listings()

        for url in all_urls:
            if url in seen_urls:
                continue

            listing = scrape_listing(url)
            if listing:
                if "ALL" in selected_districts or listing["district"] in selected_districts:
                    seen_urls.add(url)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"[✅ Uyğun Elan] {listing['district']} ➤ {listing['url']}"
                    )

        await asyncio.sleep(10)

# ---------------------- TELEGRAM HANDLERS -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_tasks:
        await update.message.reply_text("ℹ️ Scraper artıq işləyir.")
        return

    task = asyncio.create_task(continuous_scrape(chat_id, context.bot, ["ALL"]))
    user_tasks[chat_id] = task
    await update.message.reply_text("✅ Scraper başladıldı: Bütün ərazilər.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_selected_districts[chat_id] = set()

    keyboard = [
        [InlineKeyboardButton(f"✅ {district}" if district in user_selected_districts[chat_id] else district,
                              callback_data=district)]
        for district in DISTRICTS
    ]
    keyboard.append([InlineKeyboardButton("🚀 Başla", callback_data="START_SCRAPER")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📍 Əraziləri seçin və sonra 'Başla' düyməsinə basın:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data == "START_SCRAPER":
        selected = list(user_selected_districts.get(chat_id, []))
        if not selected:
            await context.bot.send_message(chat_id=chat_id, text="❗Ən azı bir ərazi seçin.")
            return

        if chat_id in user_tasks:
            user_tasks[chat_id].cancel()

        await query.edit_message_text(f"✅ Seçilmiş ərazilər: {', '.join(selected)}")
        task = asyncio.create_task(continuous_scrape(chat_id, context.bot, selected))
        user_tasks[chat_id] = task
    else:
        selected = user_selected_districts.get(chat_id, set())
        if data in selected:
            selected.remove(data)
        else:
            selected.add(data)
        user_selected_districts[chat_id] = selected
        await menu(update, context)

# ---------------------- BOT LAUNCH -----------------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button))

    print("🚀 Bot is running...")
    app.run_polling()








